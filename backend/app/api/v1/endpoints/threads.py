"""Thread CRUD."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import CurrentUser, DbSession
from app.models.thread import Thread
from app.schemas.thread import ThreadCreate, ThreadOut

router = APIRouter()

def _thread_query(db, user_id):
    return db.query(Thread).filter(Thread.user_id == user_id, Thread.deleted_at.is_(None))

@router.post("", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(payload: ThreadCreate, user: CurrentUser, db: DbSession) -> Thread:
    """Create a new chat thread."""
    thread = Thread(
        user_id=user.id,
        thread_name=payload.thread_name,
    )
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return thread

@router.get("", response_model=list[ThreadOut])
def list_threads(user: CurrentUser, db: DbSession) -> list[Thread]:
    """List current user's threads (excludes soft-deleted)."""
    return _thread_query(db, user.id).order_by(Thread.updated_at.desc()).all()

@router.get("/{thread_id}", response_model=ThreadOut)
def get_thread(thread_id: int, user: CurrentUser, db: DbSession) -> Thread:
    """Get one thread by id (must own it)."""
    thread = _thread_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    return thread

@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: int, user: CurrentUser, db: DbSession) -> None:
    """Soft-delete thread (must own it)."""
    from datetime import datetime, timezone

    thread = _thread_query(db, user.id).filter(Thread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    thread.deleted_at = datetime.now(timezone.utc)
    db.commit()