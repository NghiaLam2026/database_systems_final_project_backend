"""Thread and Message schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class ThreadCreate(BaseModel):
    thread_name: str | None = Field(
        None,
        max_length=255,
        description="Optional title shown in the chat list.",
    )

class ThreadUpdate(BaseModel):
    thread_name: str | None = Field(
        None,
        max_length=255,
        description="New title; omit to leave unchanged.",
    )

class ThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    thread_name: str | None
    created_at: datetime
    updated_at: datetime

class ThreadListItemOut(ThreadOut):
    """Thread row in a paginated list, including message count for UI."""

    message_count: int = Field(0, description="Number of non-deleted messages in this thread.")

class MessageCreate(BaseModel):
    user_request: str = Field(
        ...,
        min_length=1,
        max_length=32_000,
        description="User message to send to the assistant.",
    )
    build_id: int | None = Field(
        None,
        description="Optional build to attach as context for this turn only.",
    )

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    thread_id: int
    build_id: int | None
    user_request: str
    ai_response: str | None
    created_at: datetime