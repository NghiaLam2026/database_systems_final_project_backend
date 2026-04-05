"""Gemini-backed chat replies (orchestrator entrypoint until multi-agent routing is added)."""

from __future__ import annotations
import google.generativeai as genai
import logging
from decimal import Decimal
from typing import TYPE_CHECKING
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
            lines.append(f" - {label}: {name} x{qty} (${line_total:.2f})")
        else:
            lines.append(f" - {label}: {name} x{qty}")
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

def _extract_text_from_response(response) -> str:
    try:
        text = (response.text or "").strip()
        if text:
            return text
    except ValueError:
        logger.warning("Gemini response had no text attribute (blocked or empty candidates)")

    if getattr(response, "candidates", None):
        parts: list[str] = []
        for c in response.candidates:
            if getattr(c, "content", None) and getattr(c.content, "parts", None):
                for p in c.content.parts:
                    if getattr(p, "text", None):
                        parts.append(p.text)
        if parts:
            return "\n".join(parts).strip()
    return (
        "The assistant could not produce a reply for this request "
        "(safety filters, empty response, or model error). Try rephrasing."
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
    Produce the assistant reply for this message using Gemini.

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
    user_blob = f"""## Conversation so far (thread) {history} ## Current user message {user_request} """

    if build_section:
        user_blob = f"{build_section}\n\n---\n\n{user_blob}"

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(
        settings.gemini_model,
        system_instruction=_SYSTEM_INSTRUCTION,
    )

    try:
        response = model.generate_content(
            user_blob,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=8192,
                temperature=0.7,
            ),
        )
        return _extract_text_from_response(response)
    except Exception:
        logger.exception("Gemini generate_content failed")
        return (
            "The assistant hit an error while generating a reply. Please try again in a moment."
        )