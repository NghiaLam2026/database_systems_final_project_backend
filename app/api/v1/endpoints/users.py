"""User endpoints (profile, list, and admin management)."""

from fastapi import APIRouter, HTTPException, status
from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models.base import UserRole
from app.models.user import User
from app.schemas.auth import UserCreate
from app.schemas.common import Paginated
from app.schemas.user import UserOut, UserUpdate
from app.services.auth import hash_password

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

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def admin_create_user(payload: UserCreate, db: DbSession, admin: AdminUser) -> User:
    """Admin-only: create a user account (defaults to base user role)."""
    existing = db.query(User).filter(User.email == payload.email, User.deleted_at.is_(None)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=UserRole.USER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.patch("/{user_id}/role", response_model=UserOut)
def admin_set_role(user_id: int, role: UserRole, db: DbSession, admin: AdminUser) -> User:
    """Admin-only: set a user's role."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = role
    db.commit()
    db.refresh(user)
    return user