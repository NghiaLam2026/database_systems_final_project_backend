"""Thread and Message models (thread_message: id, thread_id, user_request, ai_response, created_at, deleted_at)."""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import TimestampMixin

class Thread(Base, TimestampMixin):
    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    thread_name: Mapped[str | None] = mapped_column(nullable=True)
    user: Mapped["User"] = relationship("User", back_populates="threads")
    messages: Mapped[list["Message"]] = relationship(
        "Message",
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

class Message(Base): # messages: id, thread_id, build_id, user_request, ai_response, created_at, deleted_at (no updated_at).
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    thread_id: Mapped[int] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    build_id: Mapped[int | None] = mapped_column(
        ForeignKey("builds.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    ai_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    thread: Mapped["Thread"] = relationship("Thread", back_populates="messages")