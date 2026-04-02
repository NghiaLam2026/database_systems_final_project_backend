"""Build business logic: component resolution, validation, enrichment."""

from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.base import PartType
from app.models.build import Build, BuildPart
from app.models.component import (
    CPU,
    GPU,
    Case,
    CaseFan,
    CPUCooler,
    Memory,
    Mobo,
    PSU,
    Storage,
)

PART_TYPE_MODEL_MAP: dict[PartType, type] = {
    PartType.CPU: CPU,
    PartType.GPU: GPU,
    PartType.MOBO: Mobo,
    PartType.MEMORY: Memory,
    PartType.PSU: PSU,
    PartType.CASE: Case,
    PartType.CPU_COOLER: CPUCooler,
    PartType.CASE_FANS: CaseFan,
    PartType.STORAGE: Storage,
}

SINGULAR_PART_TYPES: set[PartType] = {
    PartType.CPU,
    PartType.GPU,
    PartType.MOBO,
    PartType.PSU,
    PartType.CASE,
    PartType.CPU_COOLER,
}

PART_TYPE_LABELS: dict[PartType, str] = {
    PartType.CPU: "CPU",
    PartType.GPU: "Video Card",
    PartType.MOBO: "Motherboard",
    PartType.MEMORY: "Memory",
    PartType.PSU: "Power Supply",
    PartType.CASE: "Case",
    PartType.CPU_COOLER: "CPU Cooler",
    PartType.CASE_FANS: "Case Fans",
    PartType.STORAGE: "Storage",
}


# ---------------------------------------------------------------------------
# Component resolution
# ---------------------------------------------------------------------------
def resolve_component(db: Session, part_type: PartType, part_id: int) -> dict | None:
    """Look up a catalog component by type and ID.  Returns {id, name, price} or None."""
    model = PART_TYPE_MODEL_MAP.get(part_type)
    if not model:
        return None
    row = db.query(model).filter(model.id == part_id).first()
    if not row:
        return None
    return {"id": row.id, "name": row.name, "price": row.price}


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_component_exists(db: Session, part_type: PartType, part_id: int) -> None:
    """Raise 404 if the referenced catalog component does not exist."""
    if resolve_component(db, part_type, part_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Component {part_id} not found in {part_type.value} catalog",
        )

def validate_singular_slot(
    db: Session,
    build_id: int,
    part_type: PartType,
    *,
    exclude_part_id: int | None = None,
) -> None:
    """Raise 409 if a singular-slot part type is already occupied in the build."""
    if part_type not in SINGULAR_PART_TYPES:
        return
    q = db.query(BuildPart).filter(
        BuildPart.build_id == build_id,
        BuildPart.part_type == part_type,
        BuildPart.deleted_at.is_(None),
    )
    if exclude_part_id is not None:
        q = q.filter(BuildPart.id != exclude_part_id)
    if q.first():
        label = PART_TYPE_LABELS.get(part_type, part_type.value)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Build already has a {label}. Remove or swap the existing one instead.",
        )


# ---------------------------------------------------------------------------
# Enrichment (part → detail dict with resolved component)
# ---------------------------------------------------------------------------
def enrich_build_part(db: Session, part: BuildPart) -> dict:
    """Return a dict suitable for BuildPartDetailOut serialisation."""
    component = resolve_component(db, part.part_type, part.part_id)
    line_total = Decimal("0")
    if component:
        line_total = component["price"] * part.quantity
    return {
        "id": part.id,
        "build_id": part.build_id,
        "part_type": part.part_type,
        "part_id": part.part_id,
        "quantity": part.quantity,
        "component": component,
        "line_total": line_total,
        "created_at": part.created_at,
    }

def get_active_parts(db: Session, build_id: int) -> list[BuildPart]:
    """Return all non-deleted parts for a build."""
    return (
        db.query(BuildPart)
        .filter(BuildPart.build_id == build_id, BuildPart.deleted_at.is_(None))
        .all()
    )


# ---------------------------------------------------------------------------
# Build-level enrichment
# ---------------------------------------------------------------------------
def get_build_detail(db: Session, build: Build) -> dict:
    """Full build with resolved parts and computed total price."""
    parts = get_active_parts(db, build.id)
    enriched = [enrich_build_part(db, p) for p in parts]
    total_price = sum((p["line_total"] for p in enriched), Decimal("0"))
    return {
        "id": build.id,
        "user_id": build.user_id,
        "build_name": build.build_name,
        "description": build.description,
        "parts": enriched,
        "total_price": total_price,
        "created_at": build.created_at,
        "updated_at": build.updated_at,
    }

def get_build_summary(db: Session, build: Build) -> dict:
    """Lighter build representation for list views (part count + total price)."""
    parts = get_active_parts(db, build.id)
    total_price = Decimal("0")
    for part in parts:
        component = resolve_component(db, part.part_type, part.part_id)
        if component:
            total_price += component["price"] * part.quantity
    return {
        "id": build.id,
        "user_id": build.user_id,
        "build_name": build.build_name,
        "description": build.description,
        "parts_count": len(parts),
        "total_price": total_price,
        "created_at": build.created_at,
        "updated_at": build.updated_at,
    }


# ---------------------------------------------------------------------------
# Clone
# ---------------------------------------------------------------------------
def clone_build(db: Session, original: Build, user_id: int) -> Build:
    """Deep-copy a build and all its active parts.  Returns the new Build."""
    clone = Build(
        user_id=user_id,
        build_name=f"{original.build_name} (copy)",
        description=original.description,
    )
    db.add(clone)
    db.flush()

    for part in get_active_parts(db, original.id):
        db.add(
            BuildPart(
                build_id=clone.id,
                part_type=part.part_type,
                part_id=part.part_id,
                quantity=part.quantity,
            )
        )

    db.commit()
    db.refresh(clone)
    return clone


# ---------------------------------------------------------------------------
# Part-type metadata (consumed by the builder UI)
# ---------------------------------------------------------------------------
def get_part_type_metadata() -> list[dict]:
    """Return ordered list of part-type descriptors for the frontend builder."""
    return [
        {
            "key": pt.value,
            "label": PART_TYPE_LABELS[pt],
            "allow_multiple": pt not in SINGULAR_PART_TYPES,
        }
        for pt in PartType
    ]