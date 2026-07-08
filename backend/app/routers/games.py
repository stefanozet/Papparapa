"""Game catalogue, session start and authoritative scoring on finish."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..games import GAMES
from ..games.difficulty import blend, stars
from ..games.levels import LEVEL_MAX
from ..games.planner import plan_run
from ..security import get_current_parent

router = APIRouter(tags=["games"])

# How much a bucket's untried prior counts against its trials when averaging a
# whole game's difficulty (keeps rarely-played buckets from being ignored).
_PRIOR_WEIGHT = 6.0


def _difficulty_report(db: Session) -> dict:
    """Calibrated difficulty per game and per bucket.

    Each bucket blends its parametric prior with the observed failure rate; the
    per-game score is the (attempts + prior-weight)-weighted mean of its
    buckets, so it starts at the parametric estimate and shifts with real play.
    """
    stats = {(s.game_key, s.bucket): s for s in db.query(models.ActivityStat).all()}
    report: dict = {}
    for key, game in GAMES.items():
        buckets = game.difficulty_buckets()
        rows = []
        for bucket, prior in sorted(buckets.items(), key=lambda kv: kv[1]):
            s = stats.get((key, bucket))
            attempts = s.attempts if s else 0
            failures = s.failures if s else 0
            calibrated = blend(prior, attempts, failures)
            rows.append({
                "bucket": bucket,
                "prior": round(prior, 3),
                "attempts": attempts,
                "failures": failures,
                "difficulty": round(calibrated, 3),
                "stars": stars(calibrated),
            })
        weight = sum(r["attempts"] + _PRIOR_WEIGHT for r in rows)
        overall = (
            sum(r["difficulty"] * (r["attempts"] + _PRIOR_WEIGHT) for r in rows) / weight
            if weight else 0.0
        )
        report[key] = {
            "key": key,
            "difficulty": round(overall, 3),
            "stars": stars(overall),
            "attempts": sum(r["attempts"] for r in rows),
            "calibrated": game.calibrated,
            "buckets": rows,
        }
    return report


def _record_trials(db: Session, game, by_id: dict, results) -> None:
    """Aggregate this session's answers into per-bucket attempt/failure counts."""
    deltas: dict[str, list[int]] = {}
    priors: dict[str, float] = {}
    for item in results:
        activity = by_id.get(item.id)
        if activity is None or "bucket" not in activity:
            continue
        bucket = activity["bucket"]
        priors[bucket] = float(activity.get("difficulty", 0.0))
        d = deltas.setdefault(bucket, [0, 0])
        d[0] += 1
        if not game.validate(activity, item.answer):
            d[1] += 1

    for bucket, (attempts, failures) in deltas.items():
        row = (
            db.query(models.ActivityStat)
            .filter_by(game_key=game.key, bucket=bucket)
            .one_or_none()
        )
        if row is None:
            row = models.ActivityStat(
                game_key=game.key, bucket=bucket, prior=priors[bucket],
                attempts=0, failures=0,
            )
            db.add(row)
        row.attempts += attempts
        row.failures += failures
        row.prior = priors[bucket]


@router.get("/games")
def list_games(db: Session = Depends(get_db)):
    """Public catalogue used to render the game menu (no auth needed)."""
    report = _difficulty_report(db)
    games = []
    for g in GAMES.values():
        meta = g.meta()
        r = report.get(g.key, {})
        meta["difficulty"] = r.get("difficulty", 0.0)
        meta["stars"] = r.get("stars", 1)
        games.append(meta)
    # The menu shows the easiest games first.
    games.sort(key=lambda m: m["difficulty"])
    return {"games": games}


@router.get("/games/{key}/{asset}", include_in_schema=False)
def game_asset(key: str, asset: str):
    """Serve a bundled game's JS (its renderer.js and any local module it
    imports relatively, e.g. ``./logic.js``).

    Only ``.js`` files sitting flat inside a registered game's own folder are
    ever served: the key is looked up in the registry and the asset name
    admits no separators, so no arbitrary path can be requested.
    """
    game = GAMES.get(key)
    if game is None or game.renderer_path is None:
        raise HTTPException(404, "No bundled assets for this game")
    if not asset.endswith(".js") or "/" in asset or "\\" in asset or ".." in asset:
        raise HTTPException(404, "Not found")
    path = game.renderer_path.parent / asset
    if not path.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(path, media_type="text/javascript")


@router.get("/runs/plan")
def plan_full_run(
    child_id: int,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    """Plan of a full partita for this child: ordered ``{key, level_delta}``.

    The order comes from the calibrated difficulty (easy first, with a little
    randomness); the closing entries re-propose the easiest games in a harder
    mode via ``level_delta`` — see ``games/planner.py`` for the policy.
    """
    child = db.get(models.ChildProfile, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(404, "Child profile not found")
    report = _difficulty_report(db)
    # Advanced games live outside the partita: they are played on demand
    # from their own page.
    difficulties = {
        key: r["difficulty"]
        for key, r in report.items()
        if not GAMES[key].advanced
    }
    return {"plan": plan_run(difficulties)}


@router.get("/games/difficulty")
def games_difficulty(db: Session = Depends(get_db)):
    """Difficulty analytics: calibrated score per game and per parameter bucket."""
    return {"games": _difficulty_report(db)}


@router.post("/games/{key}/start", response_model=schemas.StartOut)
def start_game(
    key: str,
    child_id: int,
    level_delta: int = 0,
    parent: models.Parent = Depends(get_current_parent),
    db: Session = Depends(get_db),
):
    game = GAMES.get(key)
    if game is None:
        raise HTTPException(404, "Unknown game")

    child = db.get(models.ChildProfile, child_id)
    if child is None or child.parent_id != parent.id:
        raise HTTPException(404, "Child profile not found")

    # Resume from the child's best level in this game (1 the first time).
    # The planner can ask for a harder re-proposal via level_delta (never
    # easier: progress is only raised, and the ladder is capped at 10).
    stored = (
        db.query(models.GameLevel)
        .filter_by(child_id=child.id, game_key=key)
        .one_or_none()
    )
    start_level = min(LEVEL_MAX, (stored.level if stored else 1) + max(0, level_delta))

    activities = game.generate(start_level)
    session = models.GameSession(
        child_id=child.id,
        game_key=key,
        spec={"activities": activities, "start_level": start_level},
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return schemas.StartOut(
        session_id=session.id,
        game=game.meta(),
        tutorial=game.tutorial(),
        activities=activities,
        start_level=start_level,
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

    # Authoritative scoring: each game replays the submitted results itself
    # (the default validates answers and replays the level/streak rules;
    # self-scored games run their own simulation — see Game.score_session).
    played = game.score_session(
        by_id, payload.results, int(session.spec.get("start_level", 1))
    )
    correct = played["correct"]

    session.score = played["score"]
    session.correct_count = correct
    session.error_count = payload.errors
    session.ended_reason = payload.ended_reason
    session.status = "finished"
    session.finished_at = datetime.utcnow()

    # Persist the child's best level so the next run resumes from there.
    row = (
        db.query(models.GameLevel)
        .filter_by(child_id=session.child_id, game_key=session.game_key)
        .one_or_none()
    )
    if row is None:
        row = models.GameLevel(
            child_id=session.child_id, game_key=session.game_key, level=played["level"]
        )
        db.add(row)
    elif played["level"] > row.level:
        row.level = played["level"]

    # Feed the answers back into the difficulty model (games with a clean
    # per-answer success/failure signal only — see ChoiceGame.calibrated).
    if game.calibrated:
        _record_trials(db, game, by_id, payload.results)

    db.commit()

    return schemas.FinishOut(
        session_id=session.id,
        score=session.score,
        correct_count=correct,
        errors=payload.errors,
        ended_reason=payload.ended_reason,
        level=played["level"],
        max_level=row.level,
    )
