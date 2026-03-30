"""Auth: register, login, current-user."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import DbSession, get_current_user
from app.models.user import User
from app.schemas.auth import LoginResponse, UserCreate, UserLogin
from app.schemas.user import UserOut
from app.services.auth import create_access_token, hash_password, verify_password

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> User:
    """Create a new user account. Client should call /login afterwards."""
    existing = db.query(User).filter(
        User.email == payload.email,
        User.deleted_at.is_(None),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login", response_model=LoginResponse)
def login(payload: UserLogin, db: DbSession) -> dict:
    """Authenticate and return JWT access token with user info."""
    user = db.query(User).filter(
        User.email == payload.email,
        User.deleted_at.is_(None),
    ).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "user": user,
    }

@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    """Return current authenticated user."""
    return user