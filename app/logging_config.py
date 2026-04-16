"""Logging configuration for the FastAPI backend.

Design goals (practical, low-noise):
- Contextual binding (request_id, user_id, thread_id, etc.) without repeating fields.
- Short request ids in the dev console; full ids available for structured output.
- DEBUG for chatty request lifecycle; INFO for business/agent events.
- Suppress library noise (e.g. httpx INFO lines).

Implementation:
- `structlog` + `structlog.contextvars` for request-scoped context.
- stdlib `logging` is still the backend transport (handlers/levels).
"""

from __future__ import annotations

import logging
from logging.config import dictConfig

import structlog


def _short_request_id(_, __, event_dict: dict) -> dict:
    """Add a compact request id field for console output.

    Keep the full `request_id` intact for JSON/aggregators, but also add `req`
    with the first 8 chars so logs stay readable in the terminal.
    """
    rid = event_dict.get("request_id")
    if isinstance(rid, str) and rid:
        event_dict.setdefault("req", rid[:8])
    else:
        event_dict.setdefault("req", "-")
    return event_dict


def configure_logging(*, level: str = "INFO") -> None:
    """Configure logging once for the whole process."""
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {"format": "%(message)s"},
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "plain",
                }
            },
            "root": {"handlers": ["console"], "level": level},
            "loggers": {
                # Reduce noise from libraries; keep errors visible.
                "uvicorn.access": {"level": "WARNING"},
                "uvicorn.error": {"level": level},
                "httpx": {"level": "WARNING"},
            },
        }
    )

    # If uvicorn config has already set handlers, this still ensures structured output.
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _short_request_id,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            # Development-friendly renderer. If you later want JSON in prod, switch
            # this renderer based on an env flag.
            structlog.dev.ConsoleRenderer(colors=True),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def log() -> structlog.stdlib.BoundLogger:
    """Convenience accessor for a module logger."""
    return structlog.get_logger()