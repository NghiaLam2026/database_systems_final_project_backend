"""PC build assistant orchestrator using Pydantic AI + Google Gemini.

Uses `GoogleModel` / `GoogleProvider` (Gemini Developer API via `google-genai` under the hood).
See: https://ai.pydantic.dev/models/google/

SQL/RAG tools can be added later as `@agent.tool` hooks or sub-agents.
"""

from __future__ import annotations
import logging
from decimal import Decimal
from typing import TYPE_CHECKING
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from app.models.build import Build
from app.models.thread import Message
from app.services.build import PART_TYPE_LABELS, get_build_detail

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.config import Settings

logger = logging.getLogger(__name__)

_MAX_PRIOR_TURNS = 15
_SYSTEM_INSTRUCTION = """You are a helpful PC building assistant for a web app that manages custom PC builds \
and a parts catalog. Answer clearly and concisely. When the user attaches a build, use that parts list \
for compatibility, upgrades, and budget advice. If a question is general hardware knowledge, answer \
without requiring database access. Do not invent exact stock or prices; say when figures may be outdated."""

def _format_build_for_prompt(db: "Session", build: Build) -> str:
    detail = get_build_detail(db, build)
    lines: list[str] = [
        f"Build name: {detail['build_name']}",
    ]
    if detail.get("description"):
        lines.append(f"Description: {detail['description']}")
    lines.append(f"Estimated total (from catalog prices): ${detail['total_price']:.2f}")
    lines.append("Parts:")
    for p in detail["parts"]:
        label = PART_TYPE_LABELS.get(p["part_type"], p["part_type"].value)
        comp = p.get("component") or {}
        name = comp.get("name") or f"(missing catalog id {p['part_id']})"
        qty = p["quantity"]
        price = comp.get("price")
        if price is not None:
            line_total = Decimal(str(price)) * qty
            lines.append(f"  - {label}: {name} x{qty} (${line_total:.2f})")
        else:
            lines.append(f"  - {label}: {name} x{qty}")
    return "\n".join(lines)

def _prior_turns_block(db: "Session", *, thread_id: int, before_message_id: int) -> str:
    prior = (
        db.query(Message)
        .filter(
            Message.thread_id == thread_id,
            Message.deleted_at.is_(None),
            Message.id != before_message_id,
        )
        .order_by(Message.created_at.desc())
        .limit(_MAX_PRIOR_TURNS)
        .all()
    )
    prior = list(reversed(prior))
    if not prior:
        return "(no prior messages in this thread)"
    chunks: list[str] = []
    for m in prior:
        chunks.append(f"User: {m.user_request}")
        if m.ai_response:
            chunks.append(f"Assistant: {m.ai_response}")
        else:
            chunks.append("Assistant: (no reply recorded)")
    return "\n\n".join(chunks)

def _build_agent(settings: "Settings") -> Agent[None, str]:
    """Single-turn agent (no tools yet). New instance per request keeps API key / model changes simple."""
    provider = GoogleProvider(api_key=settings.gemini_api_key)
    model = GoogleModel(settings.gemini_model, provider=provider)
    model_settings = GoogleModelSettings(temperature=0.7, max_tokens=8192)
    return Agent(
        model,
        instructions=_SYSTEM_INSTRUCTION,
        model_settings=model_settings,
    )

def generate_chat_reply(
    db: "Session",
    settings: "Settings",
    *,
    thread_id: int,
    message: Message,
    user_request: str,
) -> str:
    """
    Produce the assistant reply for this message using Pydantic AI + Gemini.

    If GEMINI_API_KEY is unset, returns a short notice instead of calling the API.
    """
    if not settings.gemini_api_key:
        return (
            "AI replies are disabled: set GEMINI_API_KEY in the server environment to enable Gemini."
        )

    build_section = ""
    if message.build_id is not None:
        b = db.query(Build).filter(Build.id == message.build_id, Build.deleted_at.is_(None)).first()
        if b:
            build_section = (
                "The user attached the following PC build as context for this message only:\n\n"
                + _format_build_for_prompt(db, b)
            )
        else:
            build_section = "The user attached a build, but it could not be loaded."

    history = _prior_turns_block(db, thread_id=thread_id, before_message_id=message.id)
    user_blob = f"""## Conversation so far (thread)
{history}

## Current user message
{user_request}
"""

    if build_section:
        user_blob = f"{build_section}\n\n---\n\n{user_blob}"

    try:
        agent = _build_agent(settings)
        result = agent.run_sync(user_blob)
        out = (result.output or "").strip()
        if out:
            return out
        return (
            "The assistant returned an empty reply. Try rephrasing or shortening your message."
        )
    except Exception:
        logger.exception("Pydantic AI / Gemini run failed")
        return (
            "The assistant hit an error while generating a reply. Please try again in a moment."
        )