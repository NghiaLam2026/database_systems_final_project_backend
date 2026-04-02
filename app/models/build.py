"""Build and BuildPart models."""

from __future__ import annotations
from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.models.base import PartType, TimestampMixin

class Build(Base, TimestampMixin):
    __tablename__ = "builds"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    build_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="builds")
    parts: Mapped[list["BuildPart"]] = relationship(
        "BuildPart",
        back_populates="build",
        cascade="all, delete-orphan",
    )

class BuildPart(Base, TimestampMixin):
    __tablename__ = "build_parts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    build_id: Mapped[int] = mapped_column(
        ForeignKey("builds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    part_type: Mapped[PartType] = mapped_column(
        Enum(PartType, name="part_type", create_type=False,
             values_callable=lambda pt: [e.value for e in pt]),
        nullable=False,
    )
    part_id: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    build: Mapped["Build"] = relationship("Build", back_populates="parts")