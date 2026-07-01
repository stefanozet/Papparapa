"""Game catalogue, session start and authoritative scoring on finish."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import POINTS_PER_ACTIVITY
from ..database import get_db
from ..games import DEFAULT_RUN, GAMES
from ..security import get_current_parent

router = APIRouter(tags=["games"])


@router.get("/games")
def list_games():
    """Public catalogue used to render the game menu (no auth needed)."""
    return {
        "games": [g.meta() for g in GAMES.values()],
        "default_run": DEFAULT_RUN,
    }


@router.post("/games/{key}/start", response_model=schemas.StartOut)
def start_game(
    key: str,
    child_id: int,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    game = GAMES.get(key)
    if game is None:
        raise HTTPException(404, "Unknown game")

    child = db.get(models.ChildProfile, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(404, "Child profile not found")

    activities = game.generate()
    session = models.GameSession(
        child_id=child.id, game_key=key, spec={"activities": activities}
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return schemas.StartOut(
        session_id=session.id,
        game=game.meta(),
        tutorial=game.tutorial(),
        activities=activities,
    )


@router.post("/sessions/{session_id}/finish", response_model=schemas.FinishOut)
def finish_game(
    session_id: int,
    payload: schemas.FinishIn,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    session = db.get(models.GameSession, session_id)
    if session is None or session.child.parent_id != parent.id:
        raise HTTPException(404, "Session not found")
    if session.status == "finished":
        raise HTTPException(409, "Session already finished")

    game = GAMES[session.game_key]
    by_id = {a["id"]: a for a in session.spec["activities"]}

    correct = 0
    for item in payload.results:
        activity = by_id.get(item.id)
        if activity is not None and game.validate(activity, item.answer):
            correct += 1

    session.score = correct * POINTS_PER_ACTIVITY
    session.correct_count = correct
    session.error_count = payload.errors
    session.ended_reason = payload.ended_reason
    session.status = "finished"
    session.finished_at = datetime.utcnow()
    db.commit()

    return schemas.FinishOut(
        session_id=session.id,
        score=session.score,
        correct_count=correct,
        errors=payload.errors,
        ended_reason=payload.ended_reason,
    )
