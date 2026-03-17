"""Build and build_parts CRUD."""

from fastapi import APIRouter, Depends, HTTPException, status
from app.api.deps import CurrentUser, DbSession
from app.models.build import Build, BuildPart
from app.models.base import PartType
from app.schemas.build import BuildCreate, BuildOut, BuildUpdate, BuildPartCreate, BuildPartOut

router = APIRouter()

def _build_query(db, user_id):
    return db.query(Build).filter(Build.user_id == user_id, Build.deleted_at.is_(None))

@router.post("", response_model=BuildOut, status_code=status.HTTP_201_CREATED)
def create_build(payload: BuildCreate, user: CurrentUser, db: DbSession) -> Build:
    """Create a build for the current user."""
    build = Build(
        user_id=user.id,
        build_name=payload.build_name,
        description=payload.description,
    )
    db.add(build)
    db.commit()
    db.refresh(build)
    return build

@router.get("", response_model=list[BuildOut])
def list_builds(user: CurrentUser, db: DbSession) -> list[Build]:
    """List current user's builds (excludes soft-deleted)."""
    return _build_query(db, user.id).order_by(Build.updated_at.desc()).all()

@router.get("/{build_id}", response_model=BuildOut)
def get_build(build_id: int, user: CurrentUser, db: DbSession) -> Build:
    """Get one build by id (must own it)."""
    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    return build

@router.patch("/{build_id}", response_model=BuildOut)
def update_build(build_id: int, payload: BuildUpdate, user: CurrentUser, db: DbSession) -> Build:
    """Update build (must own it)."""
    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    if payload.build_name is not None:
        build.build_name = payload.build_name
    if payload.description is not None:
        build.description = payload.description
    db.commit()
    db.refresh(build)
    return build

@router.delete("/{build_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_build(build_id: int, user: CurrentUser, db: DbSession) -> None:
    """Soft-delete build (must own it)."""
    from datetime import datetime, timezone

    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    build.deleted_at = datetime.now(timezone.utc)
    db.commit()


# --- Build parts ---

@router.post("/{build_id}/parts", response_model=BuildPartOut, status_code=status.HTTP_201_CREATED)
def add_build_part(
    build_id: int,
    payload: BuildPartCreate,
    user: CurrentUser,
    db: DbSession,
) -> BuildPart:
    """Add a part to a build (must own build)."""
    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    part = BuildPart(
        build_id=build_id,
        part_type=payload.part_type,
        part_id=payload.part_id,
        quantity=payload.quantity,
    )
    db.add(part)
    db.commit()
    db.refresh(part)
    return part

@router.get("/{build_id}/parts", response_model=list[BuildPartOut])
def list_build_parts(build_id: int, user: CurrentUser, db: DbSession) -> list[BuildPart]:
    """List parts in a build (must own build)."""
    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    return db.query(BuildPart).filter(
        BuildPart.build_id == build_id,
        BuildPart.deleted_at.is_(None),
    ).all()

@router.delete("/{build_id}/parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_build_part(
    build_id: int,
    part_id: int,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Soft-delete a part from a build (must own build)."""
    from datetime import datetime, timezone

    build = _build_query(db, user.id).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Build not found")
    part = db.query(BuildPart).filter(
        BuildPart.build_id == build_id,
        BuildPart.id == part_id,
        BuildPart.deleted_at.is_(None),
    ).first()
    if not part:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    part.deleted_at = datetime.now(timezone.utc)
    db.commit()