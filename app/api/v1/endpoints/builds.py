"""Build and build-parts CRUD with component resolution and validation."""

from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, status
from app.api.deps import CurrentUser, DbSession
from app.models.build import Build, BuildPart
from app.schemas.build import (
    BuildCreate,
    BuildDetailOut,
    BuildPartCreate,
    BuildPartDetailOut,
    BuildPartUpdate,
    BuildSummaryOut,
    BuildUpdate,
    PartTypeInfo,
)
from app.services import build as build_service

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_query(db, user_id):
    return db.query(Build).filter(Build.user_id == user_id, Build.deleted_at.is_(None))

def _get_user_build_or_404(db, user_id: int, build_id: int) -> Build:
    build = _build_query(db, user_id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    return build

def _get_part_or_404(db, build_id: int, part_id: int) -> BuildPart:
    part = (
        db.query(BuildPart)
        .filter(
            BuildPart.build_id == build_id,
            BuildPart.id == part_id,
            BuildPart.deleted_at.is_(None),
        )
        .first()
    )
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    return part


# ---------------------------------------------------------------------------
# Part-type metadata (must be registered before /{build_id} routes)
# ---------------------------------------------------------------------------
@router.get("/part-types", response_model=list[PartTypeInfo])
def list_part_types() -> list[dict]:
    """Available component categories with singular/multiple metadata."""
    return build_service.get_part_type_metadata()


# ---------------------------------------------------------------------------
# Build CRUD
# ---------------------------------------------------------------------------
@router.post("", response_model=BuildDetailOut, status_code=status.HTTP_201_CREATED)
def create_build(payload: BuildCreate, user: CurrentUser, db: DbSession) -> dict:
    build = Build(
        user_id=user.id,
        build_name=payload.build_name,
        description=payload.description,
    )
    db.add(build)
    db.commit()
    db.refresh(build)
    return build_service.get_build_detail(db, build)

@router.get("", response_model=list[BuildSummaryOut])
def list_builds(user: CurrentUser, db: DbSession) -> list[dict]:
    """List current user's builds with summary info (total price, part count)."""
    builds = _build_query(db, user.id).order_by(Build.updated_at.desc()).all()
    return [build_service.get_build_summary(db, b) for b in builds]

@router.get("/{build_id}", response_model=BuildDetailOut)
def get_build(build_id: int, user: CurrentUser, db: DbSession) -> dict:
    """Full build detail with resolved component info and total price."""
    build = _get_user_build_or_404(db, user.id, build_id)
    return build_service.get_build_detail(db, build)

@router.patch("/{build_id}", response_model=BuildDetailOut)
def update_build(
    build_id: int, payload: BuildUpdate, user: CurrentUser, db: DbSession
) -> dict:
    build = _get_user_build_or_404(db, user.id, build_id)
    if payload.build_name is not None:
        build.build_name = payload.build_name
    if payload.description is not None:
        build.description = payload.description
    db.commit()
    db.refresh(build)
    return build_service.get_build_detail(db, build)

@router.delete("/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_build(build_id: int, user: CurrentUser, db: DbSession) -> None:
    build = _get_user_build_or_404(db, user.id, build_id)
    build.deleted_at = datetime.now(timezone.utc)
    db.commit()

@router.post(
    "/{build_id}/clone",
    response_model=BuildDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def clone_build(build_id: int, user: CurrentUser, db: DbSession) -> dict:
    """Deep-copy a build and all its parts into a new build owned by the caller."""
    original = _get_user_build_or_404(db, user.id, build_id)
    clone = build_service.clone_build(db, original, user.id)
    return build_service.get_build_detail(db, clone)


# ---------------------------------------------------------------------------
# Build parts
# ---------------------------------------------------------------------------
@router.post(
    "/{build_id}/parts",
    response_model=BuildPartDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def add_build_part(
    build_id: int,
    payload: BuildPartCreate,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Add a component to a build.

    Validates that the catalog component exists and that singular slots
    (CPU, GPU, Motherboard, PSU, Case, CPU Cooler) are not already occupied.
    """
    build = _get_user_build_or_404(db, user.id, build_id)
    build_service.validate_component_exists(db, payload.part_type, payload.part_id)
    build_service.validate_singular_slot(db, build.id, payload.part_type)

    part = BuildPart(
        build_id=build.id,
        part_type=payload.part_type,
        part_id=payload.part_id,
        quantity=payload.quantity,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return build_service.enrich_build_part(db, part)

@router.get("/{build_id}/parts", response_model=list[BuildPartDetailOut])
def list_build_parts(build_id: int, user: CurrentUser, db: DbSession) -> list[dict]:
    """List parts in a build with resolved component details."""
    _get_user_build_or_404(db, user.id, build_id)
    parts = build_service.get_active_parts(db, build_id)
    return [build_service.enrich_build_part(db, p) for p in parts]

@router.patch("/{build_id}/parts/{part_id}", response_model=BuildPartDetailOut)
def update_build_part(
    build_id: int,
    part_id: int,
    payload: BuildPartUpdate,
    user: CurrentUser,
    db: DbSession,
) -> dict:
    """Swap a component or change its quantity within a build."""
    _get_user_build_or_404(db, user.id, build_id)
    part = _get_part_or_404(db, build_id, part_id)

    if payload.part_id is not None:
        build_service.validate_component_exists(db, part.part_type, payload.part_id)
        part.part_id = payload.part_id
    if payload.quantity is not None:
        part.quantity = payload.quantity

    db.commit()
    db.refresh(part)
    return build_service.enrich_build_part(db, part)

@router.delete("/{build_id}/parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_build_part(
    build_id: int,
    part_id: int,
    user: CurrentUser,
    db: DbSession,
) -> None:
    _get_user_build_or_404(db, user.id, build_id)
    part = _get_part_or_404(db, build_id, part_id)
    part.deleted_at = datetime.now(timezone.utc)
    db.commit()