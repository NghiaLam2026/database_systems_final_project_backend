"""Build, BuildPart, and part-type metadata schemas."""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.models.base import PartType


# ---------------------------------------------------------------------------
# Resolved component (embedded inside part responses)
# ---------------------------------------------------------------------------
class ComponentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    price: Decimal


# ---------------------------------------------------------------------------
# Build Part schemas
# ---------------------------------------------------------------------------
class BuildPartCreate(BaseModel):
    part_type: PartType
    part_id: int
    quantity: int = Field(default=1, ge=1)

class BuildPartUpdate(BaseModel):
    part_id: int | None = None
    quantity: int | None = Field(default=None, ge=1)

class BuildPartDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    build_id: int
    part_type: PartType
    part_id: int
    quantity: int
    component: ComponentSummary | None
    line_total: Decimal
    created_at: datetime


# ---------------------------------------------------------------------------
# Build schemas
# ---------------------------------------------------------------------------
class BuildCreate(BaseModel):
    build_name: str
    description: str | None = None

class BuildUpdate(BaseModel):
    build_name: str | None = None
    description: str | None = None

class BuildDetailOut(BaseModel):
    """Full build with resolved parts — used for single-build responses."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    build_name: str
    description: str | None
    parts: list[BuildPartDetailOut]
    total_price: Decimal
    created_at: datetime
    updated_at: datetime

class BuildSummaryOut(BaseModel):
    """Lighter build representation for list views."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    build_name: str
    description: str | None
    parts_count: int
    total_price: Decimal
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Part-type metadata (for the builder UI category list)
# ---------------------------------------------------------------------------

class PartTypeInfo(BaseModel):
    key: str
    label: str
    allow_multiple: bool