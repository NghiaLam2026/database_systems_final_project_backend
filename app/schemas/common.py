"""Shared schemas."""

from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

class Paginated(BaseModel, Generic[T]): # Generic paginated list.
    items: list[T]
    total: int
    page: int
    size: int
    pages: int