"""User endpoints (profile, list for admin)."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.user import User
from app.schemas.common import Paginated
from app.schemas.user import UserOut, UserUpdate

router = APIRouter()

@router.get("/me", response_model=UserOut)
def get_me(user: CurrentUser) -> User:
    """Current user profile (alias for GET /auth/me)."""
    return user

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, user: CurrentUser, db: DbSession) -> User:
    """Update current user profile."""
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    db.commit()
    db.refresh(user)
    return user

@router.get("", response_model=Paginated[UserOut])
def list_users(
    db: DbSession,
    admin: AdminUser,
    page: int = 1,
    size: int = 20,
) -> Paginated[UserOut]:
    """List users (admin only). Excludes soft-deleted."""
    from sqlalchemy import func

    q = db.query(User).filter(User.deleted_at.is_(None))
    total = db.query(func.count(User.id)).filter(User.deleted_at.is_(None)).scalar() or 0
    items = q.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size if total else 0
    return Paginated(items=items, total=total, page=page, size=size, pages=pages)