"""Thread CRUD for AI chat (one thread = one chat session)."""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, status
from app.api.deps import CurrentUser, DbSession
from app.models.thread import Thread
from app.schemas.common import Paginated
from app.schemas.thread import ThreadCreate, ThreadListItemOut, ThreadOut, ThreadUpdate
from app.services.thread_service import message_counts_for_threads, soft_delete_messages_in_thread

router = APIRouter()

def _threads_base_query(db, user_id: int):
    return db.query(Thread).filter(Thread.user_id == user_id, Thread.deleted_at.is_(None))

@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(payload: ThreadCreate, user: CurrentUser, db: DbSession) -> Thread:
    """Create a new chat thread (e.g. user clicked New Chat)."""
    thread = Thread(
        user_id=user.id,
        thread_name=payload.thread_name,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

@router.get("", response_model=Paginated[ThreadListItemOut])
def list_threads(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Threads per page"),
) -> dict:
    """List the current user's threads, newest activity first."""
    q = _threads_base_query(db, user.id).order_by(Thread.updated_at.desc())
    total = q.count()
    rows = q.offset((page - 1) * size).limit(size).all()
    ids = [t.id for t in rows]
    counts = message_counts_for_threads(db, user_id=user.id, thread_ids=ids)
    pages = (total + size - 1) // size if total else 0
    items = [
        ThreadListItemOut.model_validate(
            {
                **ThreadOut.model_validate(t).model_dump(),
                "message_count": counts.get(t.id, 0),
            }
        )
        for t in rows
    ]
    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}


@router.get("/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: int, user: CurrentUser, db: DbSession) -> Thread:
    """Get one thread by id (must own it)."""
    thread = _threads_base_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread

@router.patch("/{thread_id}", response_model=ThreadOut)
def update_thread(
    thread_id: int,
    payload: ThreadUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Thread:
    """Rename a thread (e.g. after first message or user edit)."""
    thread = _threads_base_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    data = payload.model_dump(exclude_unset=True)
    if not data:
        return thread
    if "thread_name" in data:
        thread.thread_name = data["thread_name"]
    db.commit()
    db.refresh(thread)
    return thread

@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: int, user: CurrentUser, db: DbSession) -> None:
    """Soft-delete a thread and all its messages (must own the thread)."""
    thread = _threads_base_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    now = datetime.now(timezone.utc)
    soft_delete_messages_in_thread(db, thread_id=thread_id)
    thread.deleted_at = now
    db.commit()