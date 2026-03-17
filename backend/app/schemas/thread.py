"""Thread and Message schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ThreadCreate(BaseModel):
    thread_name: str | None = None

class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    thread_name: str | None
    created_at: datetime
    updated_at: datetime

class MessageCreate(BaseModel):
    user_request: str
    build_id: int | None = None

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    build_id: int | None
    user_request: str
    ai_response: str | None
    created_at: datetime