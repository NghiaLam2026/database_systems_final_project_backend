"""Input guardrails for chat / agent endpoints.

Blocks obvious prompt-injection, instruction override, and high-risk patterns
before any LLM call (saves tokens and reduces abuse). Uses a conservative
substring match on normalized text; extend via CHAT_GUARDRAIL_EXTRA_PHRASES.

When a message is blocked, the messages endpoint still returns **201** with a
normal `Message` row: `user_request` is preserved and `ai_response` is set to
`GUARDRAIL_ASSISTANT_REPLY` so chat UIs show a reply without special error handling.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)

# Shown as the assistant bubble when input is blocked (no LLM call).
GUARDRAIL_ASSISTANT_REPLY = (
    "I'm not able to help with that kind of request. Ask about PC parts, builds, "
    "compatibility, or upgrades—or try rephrasing your question."
)

# Default phrases (lowercased for comparison). Keep multi-word where possible to reduce false positives.
_DEFAULT_BLOCKED_PHRASES: tuple[str, ...] = (
    # Instruction / role override
    "ignore previous",
    "ignore all previous",
    "ignore the above",
    "disregard previous",
    "disregard all previous",
    "forget your instructions",
    "forget everything",
    "you are now",
    "you must now",
    "new instructions:",
    "override your",
    "bypass your",
    "developer mode",
    "jailbreak",
    "dan mode",
    "simulate a persona",
    "act as if you",
    "pretend you are",
    "roleplay as",
    # System / prompt exfiltration
    "system prompt",
    "reveal your instructions",
    "show me your prompt",
    "what are your rules",
    "print your system",
    "repeat the words above",
    "output the full",
    "leak your",
    # Credentials / secrets fishing
    "api key",
    "secret key",
    "password for",
    "database url",
    "connection string",
    "env variable",
    ".env",
    # Obvious code / shell abuse (future SQL/RAG safety)
    "; drop table",
    "; delete from",
    "insert into users",
    "grant all privileges",
    "exec(",
    "eval(",
    "__import__",
    "rm -rf",
    "/etc/passwd",
    "<script",
    "javascript:",
)

def _normalize_for_scan(text: str) -> str:
    """Lowercase, NFKC-normalize, collapse whitespace for reliable matching."""
    s = unicodedata.normalize("NFKC", text).lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _load_extra_phrases(settings: Settings) -> list[str]:
    raw = getattr(settings, "chat_guardrail_extra_phrases", None) or ""
    if not raw.strip():
        return []
    parts = [p.strip().lower() for p in raw.split(",")]
    return [p for p in parts if len(p) >= 3]

def scan_user_message(text: str, settings: Settings) -> str | None:
    """
    Return a short internal reason code if the message should be blocked, else None.

    Does not raise — callers decide how to respond (persist canned reply vs LLM).
    """
    if not getattr(settings, "chat_guardrail_enabled", True):
        return None

    max_len = getattr(settings, "chat_guardrail_max_message_length", 32_000)
    if len(text) > max_len:
        return "max_length"

    normalized = _normalize_for_scan(text)
    if not normalized:
        return "empty"

    phrases = list(_DEFAULT_BLOCKED_PHRASES) + _load_extra_phrases(settings)
    for phrase in phrases:
        if phrase in normalized:
            return "blocklist"

    return None

def log_guardrail_block(reason: str) -> None:
    logger.info("chat_guardrail_blocked", extra={"reason": reason})