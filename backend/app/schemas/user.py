"""User schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.base import UserRole

class UserOut(BaseModel): # User response (no password).
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    first_name: str
    last_name: str
    role: UserRole
    created_at: datetime

class UserUpdate(BaseModel): # Partial user update (e.g. profile).
    first_name: str | None = None
    last_name: str | None = None