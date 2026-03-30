"""Read-only catalog: list hardware components (no auth required for browse)."""

from decimal import Decimal
from fastapi import APIRouter, Query
from app.api.deps import DbSession
from app.models.component import (
    Mobo,
    CPU,
    Memory,
    Case,
    Storage,
    CPUCooler,
    PSU,
    CaseFan,
    GPU,
)

router = APIRouter()

# Generic list with optional price filter; all component tables have id, name, price (and others).

@router.get("/mobo", response_model=list[dict])
def list_mobo(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    """List motherboards. Optional price filter."""
    q = db.query(Mobo)
    if min_price is not None:
        q = q.filter(Mobo.price >= min_price)
    if max_price is not None:
        q = q.filter(Mobo.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/cpu", response_model=list[dict])
def list_cpu(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(CPU)
    if min_price is not None:
        q = q.filter(CPU.price >= min_price)
    if max_price is not None:
        q = q.filter(CPU.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/memory", response_model=list[dict])
def list_memory(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(Memory)
    if min_price is not None:
        q = q.filter(Memory.price >= min_price)
    if max_price is not None:
        q = q.filter(Memory.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/case", response_model=list[dict])
def list_case(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(Case)
    if min_price is not None:
        q = q.filter(Case.price >= min_price)
    if max_price is not None:
        q = q.filter(Case.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/storage", response_model=list[dict])
def list_storage(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(Storage)
    if min_price is not None:
        q = q.filter(Storage.price >= min_price)
    if max_price is not None:
        q = q.filter(Storage.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/cpu_cooler", response_model=list[dict])
def list_cpu_cooler(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(CPUCooler)
    if min_price is not None:
        q = q.filter(CPUCooler.price >= min_price)
    if max_price is not None:
        q = q.filter(CPUCooler.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/psu", response_model=list[dict])
def list_psu(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(PSU)
    if min_price is not None:
        q = q.filter(PSU.price >= min_price)
    if max_price is not None:
        q = q.filter(PSU.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/case_fans", response_model=list[dict])
def list_case_fans(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(CaseFan)
    if min_price is not None:
        q = q.filter(CaseFan.price >= min_price)
    if max_price is not None:
        q = q.filter(CaseFan.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

@router.get("/gpu", response_model=list[dict])
def list_gpu(
    db: DbSession,
    min_price: float | None = Query(None, ge=0),
    max_price: float | None = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[dict]:
    q = db.query(GPU)
    if min_price is not None:
        q = q.filter(GPU.price >= min_price)
    if max_price is not None:
        q = q.filter(GPU.price <= max_price)
    rows = q.limit(limit).all()
    return [_row_to_dict(r) for r in rows]

def _row_to_dict(row) -> dict:
    """Turn an ORM row into a JSON-serializable dict (Decimal -> float)."""
    d = {}
    for c in row.__table__.columns:
        v = getattr(row, c.name)
        if hasattr(v, "value"):  # enum
            v = v.value
        elif isinstance(v, Decimal):
            v = float(v)
        d[c.name] = v
    return d