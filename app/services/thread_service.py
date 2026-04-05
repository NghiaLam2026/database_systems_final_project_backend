"""Thread / message access helpers (ownership, soft-delete)."""

from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import func
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from app.models.thread import Message, Thread

def get_active_thread_for_user(db: Session, *, user_id: int, thread_id: int) -> Thread | None:
    """Return the thread if it exists, belongs to the user, and is not soft-deleted."""
    from app.models.thread import Thread

    return (
        db.query(Thread)
        .filter(
            Thread.id == thread_id,
            Thread.user_id == user_id,
            Thread.deleted_at.is_(None),
        )
        .first()
    )

def touch_thread_updated_at(thread: Thread) -> None:
    """Bump updated_at when the thread receives activity (e.g. new message)."""
    thread.updated_at = datetime.now(timezone.utc)

def soft_delete_messages_in_thread(db: Session, *, thread_id: int) -> int:
    """Soft-delete all active messages in a thread. Returns number of rows updated."""
    from app.models.thread import Message

    now = datetime.now(timezone.utc)
    return (
        db.query(Message)
        .filter(Message.thread_id == thread_id, Message.deleted_at.is_(None))
        .update({Message.deleted_at: now}, synchronize_session=False)
    )

def message_counts_for_threads(db: Session, *, user_id: int, thread_ids: list[int]) -> dict[int, int]:
    """Count non-deleted messages per thread, scoped to threads owned by user."""
    from app.models.thread import Message, Thread

    if not thread_ids:
        return {}
    rows = (
        db.query(Message.thread_id, func.count(Message.id))
        .join(Thread, Thread.id == Message.thread_id)
        .filter(
            Thread.user_id == user_id,
            Message.thread_id.in_(thread_ids),
            Message.deleted_at.is_(None),
            Thread.deleted_at.is_(None),
        )
        .group_by(Message.thread_id)
        .all()
    )
    return {tid: int(c) for tid, c in rows}