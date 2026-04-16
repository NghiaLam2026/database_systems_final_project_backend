"""Messages within a thread (user turns + AI replies)."""

from typing import Literal
from fastapi import APIRouter, HTTPException, Query, status
import structlog
from app.api.deps import CurrentUser, DbSession
from app.config import get_settings
from app.models.build import Build
from app.models.thread import Message
from app.schemas.common import Paginated
from app.schemas.thread import MessageCreate, MessageOut
from app.services.chat_guardrails import (
    GUARDRAIL_ASSISTANT_REPLY,
    log_guardrail_block,
    scan_user_message,
)
from app.services.chat_orchestrator import generate_chat_reply
from app.services.thread_service import get_active_thread_for_user, touch_thread_updated_at

router = APIRouter()
logger = structlog.get_logger(__name__)

def _messages_in_thread(db, thread_id: int):
    return db.query(Message).filter(Message.thread_id == thread_id, Message.deleted_at.is_(None))

@router.post("/{thread_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    thread_id: int,
    payload: MessageCreate,
    user: CurrentUser,
    db: DbSession,
) -> Message:
    """
    Append a user message to a thread and return the completed turn.

    Persists `user_request`, optionally validates `build_id`, then fills `ai_response`
    via Gemini when `GEMINI_API_KEY` is configured (see `technical_design.md`).
    """
    thread = get_active_thread_for_user(db, user_id=user.id, thread_id=thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    structlog.contextvars.bind_contextvars(
        user_id=user.id,
        thread_id=thread_id,
    )
    log = logger.bind(build_id=payload.build_id)
    log.info("chat.message_received", chars=len(payload.user_request or ""))

    if payload.build_id is not None:
        build = db.query(Build).filter(
            Build.id == payload.build_id,
            Build.user_id == user.id,
            Build.deleted_at.is_(None),
        ).first()
        if not build:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid build_id: build not found or not owned by you",
            )

    settings = get_settings()
    block_reason = scan_user_message(payload.user_request, settings)
    if block_reason is not None:
        log.info("chat.guardrail_blocked", reason=block_reason)
        log_guardrail_block(block_reason)
        msg = Message(
            thread_id=thread_id,
            build_id=payload.build_id,
            user_request=payload.user_request,
            ai_response=GUARDRAIL_ASSISTANT_REPLY,
        )
        db.add(msg)
        touch_thread_updated_at(thread)
        db.commit()
        db.refresh(msg)
        return msg

    msg = Message(
        thread_id=thread_id,
        build_id=payload.build_id,
        user_request=payload.user_request,
        ai_response=None,
    )
    db.add(msg)
    touch_thread_updated_at(thread)
    db.commit()
    db.refresh(msg)

    structlog.contextvars.bind_contextvars(message_id=msg.id, user_role=user.role.value)
    msg.ai_response = generate_chat_reply(
        db,
        settings,
        thread_id=thread_id,
        message=msg,
        user_request=payload.user_request,
        user_role=user.role.value,
    )
    db.commit()
    db.refresh(msg)

    return msg

@router.get("/{thread_id}/messages", response_model=Paginated[MessageOut])
def list_messages(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    order: Literal["asc", "desc"] = Query(
        "asc",
        description="Sort by created_at: asc (oldest first, typical chat order) or desc.",
    ),
) -> dict:
    """List messages in a thread (must own the thread). Paginated, ordered by time."""
    thread = get_active_thread_for_user(db, user_id=user.id, thread_id=thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    q = _messages_in_thread(db, thread_id)
    total = q.count()
    q = q.order_by(Message.created_at.asc() if order == "asc" else Message.created_at.desc())
    rows = q.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size if total else 0
    return {"items": rows, "total": total, "page": page, "size": size, "pages": pages}

@router.get("/{thread_id}/messages/{message_id}", response_model=MessageOut)
def get_message(
    thread_id: int,
    message_id: int,
    user: CurrentUser,
    db: DbSession,
) -> Message:
    """Fetch a single message if it belongs to a thread you own."""
    thread = get_active_thread_for_user(db, user_id=user.id, thread_id=thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    msg = (
        _messages_in_thread(db, thread_id)
        .filter(Message.id == message_id)
        .first()
    )
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return msg