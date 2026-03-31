"""Read-only catalog: browse hardware components (no auth required)."""

from enum import Enum
from typing import Any
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.deps import DbSession
from app.db.base import Base
from app.models.component import (
    CPU, GPU, Case, CaseFan, CPUCooler, Memory, Mobo, PSU, Storage,
)
from app.schemas.catalog import (
    CPUOut, GPUOut, CaseOut, CaseFanOut, CPUCoolerOut,
    MemoryOut, MoboOut, PSUOut, StorageOut,
)
from app.schemas.common import Paginated

router = APIRouter()

class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"

_CATALOG_REGISTRY: dict[str, dict[str, Any]] = {
    "cpu":        {"model": CPU,       "schema": CPUOut},
    "gpu":        {"model": GPU,       "schema": GPUOut},
    "mobo":       {"model": Mobo,      "schema": MoboOut},
    "memory":     {"model": Memory,    "schema": MemoryOut},
    "psu":        {"model": PSU,       "schema": PSUOut},
    "case":       {"model": Case,      "schema": CaseOut},
    "cpu_cooler": {"model": CPUCooler, "schema": CPUCoolerOut},
    "case_fans":  {"model": CaseFan,   "schema": CaseFanOut},
    "storage":    {"model": Storage,   "schema": StorageOut},
}

def _list_components(
    db: Session,
    model: type[Base],
    page: int,
    size: int,
    min_price: float | None,
    max_price: float | None,
    search: str | None,
    sort_by: str,
    order: SortOrder,
) -> dict:
    q = db.query(model)
    count_q = db.query(func.count(model.id))

    if min_price is not None:
        q = q.filter(model.price >= min_price)
        count_q = count_q.filter(model.price >= min_price)
    if max_price is not None:
        q = q.filter(model.price <= max_price)
        count_q = count_q.filter(model.price <= max_price)

    if search and hasattr(model, "name"):
        pattern = f"%{search}%"
        q = q.filter(model.name.ilike(pattern))
        count_q = count_q.filter(model.name.ilike(pattern))

    valid_columns = {c.name for c in model.__table__.columns}
    if sort_by not in valid_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by column '{sort_by}'. Valid columns: {sorted(valid_columns)}",
        )
    sort_col = getattr(model, sort_by)
    q = q.order_by(sort_col.asc() if order == SortOrder.asc else sort_col.desc())

    total = count_q.scalar() or 0
    items = q.offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size if total else 0

    return {"items": items, "total": total, "page": page, "size": size, "pages": pages}

def _get_component(db: Session, model: type[Base], component_id: int):
    row = db.query(model).filter(model.id == component_id).first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Component not found",
        )
    return row

def _register_routes(
    key: str,
    model: type[Base],
    schema: type[BaseModel],
) -> None:
    """Register list + detail routes for a component type."""

    @router.get(
        f"/{key}",
        response_model=Paginated[schema],
        summary=f"List {key} components",
        name=f"list_{key}",
    )
    def list_items(
        db: DbSession,
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=200, description="Items per page"),
        min_price: float | None = Query(None, ge=0, description="Minimum price filter"),
        max_price: float | None = Query(None, ge=0, description="Maximum price filter"),
        search: str | None = Query(None, min_length=1, max_length=100, description="Search by name"),
        sort_by: str = Query("price", description="Column to sort by (e.g. price, name)"),
        order: SortOrder = Query(SortOrder.asc, description="Sort order"),
    ) -> dict:
        return _list_components(db, model, page, size, min_price, max_price, search, sort_by, order)

    @router.get(
        f"/{key}/{{component_id}}",
        response_model=schema,
        summary=f"Get {key} by ID",
        name=f"get_{key}",
    )
    def get_item(
        component_id: int,
        db: DbSession,
    ):
        return _get_component(db, model, component_id)

for _key, _conf in _CATALOG_REGISTRY.items():
    _register_routes(_key, _conf["model"], _conf["schema"])