"""SQLAlchemy declarative base. Import all models here for Alembic autogenerate."""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass