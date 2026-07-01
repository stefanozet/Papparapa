"""Child profile management and per-child statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..security import get_current_parent

router = APIRouter(tags=["profiles"])


def _owned_child(child_id: int, parent: models.Parent, db: Session) -> models.ChildProfile:
    child = db.get(models.ChildProfile, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(404, "Child profile not found")
    return child


@router.get("/profiles", response_model=list[schemas.ChildOut])
def list_children(
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.ChildProfile)
        .filter(models.ChildProfile.parent_id == parent.id)
        .order_by(models.ChildProfile.id)
        .all()
    )


@router.post("/profiles", response_model=schemas.ChildOut, status_code=201)
def create_child(
    payload: schemas.ChildIn,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    child = models.ChildProfile(
        parent_id=parent.id, name=payload.name.strip(), avatar=payload.avatar
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.get("/profiles/{child_id}/stats", response_model=schemas.StatsOut)
def child_stats(
    child_id: int,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    child = _owned_child(child_id, parent, db)
    sessions = [s for s in child.sessions if s.status == "finished"]
    games: dict[str, dict[str, int]] = {}
    for s in sessions:
        g = games.setdefault(s.game_key, {"best": 0, "plays": 0, "total": 0})
        g["plays"] += 1
        g["total"] += s.score
        g["best"] = max(g["best"], s.score)
    return schemas.StatsOut(
        total_score=sum(s.score for s in sessions),
        plays=len(sessions),
        games=games,
    )
