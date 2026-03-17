"""Build and BuildPart schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.base import PartType

class BuildPartCreate(BaseModel): # Add a part to a build
    part_type: PartType
    part_id: int
    quantity: int = 1

class BuildPartOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    build_id: int
    part_type: PartType
    part_id: int
    quantity: int
    created_at: datetime

class BuildCreate(BaseModel): # Create a build payload.
    build_name: str
    description: str | None = None

class BuildUpdate(BaseModel): # Update a build payload.

    build_name: str | None = None
    description: str | None = None

class BuildOut(BaseModel): # Build response
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    build_name: str
    description: str | None
    created_at: datetime
    updated_at: datetime