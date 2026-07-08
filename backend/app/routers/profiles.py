"""Child profile management and per-child statistics."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..games import GAMES
from ..security import get_current_parent

router = APIRouter(tags=["profiles"])

# Advanced games keep a personal best but stay out of the shared ⭐ economy:
# their sessions never count toward total scores or the leaderboard.
_ADVANCED_KEYS = frozenset(k for k, g in GAMES.items() if g.advanced)


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


@router.get("/leaderboard", response_model=list[schemas.LeaderboardEntry])
def leaderboard(
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """Global ranking across every child, by total score of finished games.

    Children who have not played yet appear with 0 points, so a new player
    still finds themself on the board.
    """
    total = func.coalesce(func.sum(models.GameSession.score), 0).label("total")
    joined = (
        (models.GameSession.child_id == models.ChildProfile.id)
        & (models.GameSession.status == "finished")
    )
    if _ADVANCED_KEYS:
        joined = joined & models.GameSession.game_key.notin_(_ADVANCED_KEYS)
    rows = (
        db.query(models.ChildProfile, total)
        .outerjoin(models.GameSession, joined)
        .group_by(models.ChildProfile.id)
        .order_by(total.desc(), models.ChildProfile.id)
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [
        schemas.LeaderboardEntry(
            child_id=child.id, name=child.name, avatar=child.avatar, total_score=score
        )
        for child, score in rows
    ]


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
    # The per-game breakdown keeps the advanced games' personal bests, but
    # their points stay out of the child's ⭐ total (separate economy).
    return schemas.StatsOut(
        total_score=sum(s.score for s in sessions if s.game_key not in _ADVANCED_KEYS),
        plays=len(sessions),
        games=games,
    )
