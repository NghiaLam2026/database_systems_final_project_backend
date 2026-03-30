"""Shared mixins and enums for models."""

import enum
from datetime import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

class PartType(str, enum.Enum): # Component type for build_parts. Must match DB enum 'part_type'.
    CPU = "cpu"
    GPU = "gpu"
    MOBO = "mobo"
    MEMORY = "memory"
    PSU = "psu"
    CASE = "case"
    CPU_COOLER = "cpu_cooler"
    CASE_FANS = "case_fans"
    STORAGE = "storage"

class UserRole(str, enum.Enum): # User role. Must match DB enum 'user_role'.
    USER = "user"
    ADMIN = "admin"

class TimestampMixin: # created_at, updated_at, deleted_at for soft-delete support.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )