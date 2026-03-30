"""Message CRUD and send (orchestrator stub)."""

from fastapi import APIRouter, HTTPException, status
from app.api.deps import CurrentUser, DbSession
from app.models.build import Build
from app.models.thread import Thread, Message
from app.schemas.thread import MessageCreate, MessageOut

router = APIRouter()

def _thread_query(db, user_id):
    return db.query(Thread).filter(Thread.user_id == user_id, Thread.deleted_at.is_(None))

@router.post("/{thread_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message(
    thread_id: int,
    payload: MessageCreate,
    user: CurrentUser,
    db: DbSession,
) -> Message:
    """Create a message in a thread and return it. AI response is stubbed until orchestrator is wired."""
    thread = _thread_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    if payload.build_id is not None:
        build = db.query(Build).filter(
            Build.id == payload.build_id,
            Build.user_id == user.id,
            Build.deleted_at.is_(None),
        ).first()
        if not build:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Build not found")

    msg = Message(
        thread_id=thread_id,
        build_id=payload.build_id,
        user_request=payload.user_request,
        ai_response=None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # TODO: Call orchestrator with msg.build_id and recent thread context; then update msg.ai_response.
    # For now, stub a placeholder response.
    msg.ai_response = "[AI response placeholder – orchestrator not yet wired]"
    db.commit()
    db.refresh(msg)

    return msg

@router.get("/{thread_id}/messages", response_model=list[MessageOut])
def list_messages(
    thread_id: int,
    user: CurrentUser,
    db: DbSession,
    limit: int = 50,
) -> list[Message]:
    """List messages in a thread (must own thread). Excludes soft-deleted."""
    thread = _thread_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return (
        db.query(Message)
        .filter(Message.thread_id == thread_id, Message.deleted_at.is_(None))
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )