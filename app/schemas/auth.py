"""Auth-related schemas."""

from pydantic import BaseModel, EmailStr, Field

from app.models.base import UserRole


class UserCreate(BaseModel):
    """Registration payload."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)


class AdminUserCreate(BaseModel):
    """Admin-only user creation payload (supports optional role)."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: UserRole = UserRole.USER


class UserLogin(BaseModel):
    """Login payload."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login response with token and user info."""
    access_token: str
    token_type: str = "bearer"
    user: "UserOutNested"


class UserOutNested(BaseModel):
    """Minimal user info embedded in login response."""
    model_config = {"from_attributes": True}

    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole


class TokenPayload(BaseModel):
    """Decoded JWT payload (for dependency)."""
    sub: int
    role: str
    exp: int