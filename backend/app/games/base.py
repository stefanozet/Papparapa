"""Abstract game definitions.

Every game produces an ordered list of *micro-activities* of the same type.
The frontend engine plays them one after another under a time limit; reaching
``max_errors`` mistakes ends the game.  To add a new game, drop a module (or
package) into ``catalog/`` subclassing ``Game`` (or ``ChoiceGame``) — it is
discovered automatically; see ``catalog/README.md`` for the full recipe.

Rendering (``kind``)
--------------------
``kind`` names the interaction the frontend renders: every activity of a game
carries it, and the engine loads ``frontend/js/games/<kind>.js`` to play it.
A game either reuses one of the app's base kinds or ships its own dynamics as
a ``renderer.js`` file inside its catalog folder (the registry detects it and
``meta()`` then points the frontend at ``renderer_url`` instead).

Procedural generation & difficulty
----------------------------------
A game is built *procedurally* from a set of parameter **buckets** exposed by
``difficulty_buckets()`` — each bucket maps a signature of the creation
parameters to a parametric difficulty in ``[0, 1]``. ``generate(start_level)``
emits a batch of activities for every level from ``start_level`` up to 10,
picking for each level the bucket nearest to its target difficulty (see
``levels.py``), so every activity carries the ``level``, ``bucket`` and
``difficulty`` it was built from. Trials are then aggregated per bucket to
calibrate the score empirically (see ``difficulty.py``).

Activity dict shapes
--------------------
choice : ``{"id": int, "level": int, "bucket": str, "difficulty": float,
            "kind": "choice", "stimulus": [str], "options": [str],
            "answer": int}``
memory : like choice, but ``kind: "memory"`` plus ``peek_ms`` — the stimulus
         is shown for that long, then masked before the options appear
memo   : ``{"kind": "memo", "cards": [str], "max_errors": int}`` — each
         picture appears twice; ``max_errors`` (= pairs) is the board's own
         wrong-pair budget, refreshed per board; the result is
         client-reported (``{"solved": bool}``) like the maze
simon  : ``{"kind": "simon", "pads": [str], "sequence": [int]}`` — the answer
         is the list of tapped pad indexes, checked against ``sequence``
maze   : ``{"kind": "maze", "grid": [str], "start": [r, c], "exit": [r, c]}``
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .. import config
from .difficulty import nearest_bucket
from .levels import LEVEL_MAX, replay, target_difficulty


class Game(ABC):
    key: str
    name: str
    icon: str                 # emoji shown in menus (visual, wordless)
    color: str                # theme color (hex)
    kind: str                 # interaction rendered by the frontend (see module docstring)
    renderer_path: Path | None = None  # bundled renderer.js, set by the registry
    # Advanced games live on their own menu page, are excluded from the
    # planner's full run and their scores stay out of the ⭐ totals and the
    # leaderboard (per-game personal best only).
    advanced: bool = False
    # Self-scored games award their own points live (ctx.addPoints in the
    # frontend) instead of the shared points/streak/level ladder; they must
    # override ``score_session`` with their own authoritative replay.
    self_scored: bool = False
    timed: bool = True        # every game runs against the clock
    duration_seconds: int = 15  # each game lasts this long, then the run moves on
    activities_per_level: int = 8  # plenty per level: the timer, not the list, ends it
    max_errors: int = 3
    calibrated: bool = False  # True → user trials refine this game's difficulty

    @abstractmethod
    def difficulty_buckets(self) -> dict[str, float]:
        """Map each generation *bucket* (a signature of the creation
        parameters) to its parametric difficulty in ``[0, 1]``."""

    @abstractmethod
    def _one(self, bucket: str) -> dict[str, Any]:
        """Build a single activity for the given difficulty ``bucket``.

        Return only the activity *content* (``kind`` and its fields); the
        ``id``, ``level``, ``bucket`` and ``difficulty`` are attached by
        ``generate``.
        """

    @abstractmethod
    def tutorial(self) -> dict[str, Any]:
        """Return one simple sample activity for the wordless animated demo."""

    @abstractmethod
    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        """Return ``True`` when ``answer`` solves ``activity`` correctly."""

    def generate(self, start_level: int = 1) -> list[dict[str, Any]]:
        """A batch of activities for every level from ``start_level`` to 10.

        The player works through one level's batch at a time; levelling up
        (see ``levels.py``) jumps to the next batch.
        """
        buckets = self.difficulty_buckets()
        # In quota mode every level batch must hold at least the whole quota:
        # slow games (memo, maze) keep smaller batches only under the timer.
        per_level = max(self.activities_per_level, config.QUIZZES_PER_GAME)
        out: list[dict[str, Any]] = []
        for level in range(max(1, min(LEVEL_MAX, start_level)), LEVEL_MAX + 1):
            bucket = nearest_bucket(target_difficulty(level), buckets)
            for _ in range(per_level):
                out.append(
                    {
                        "id": len(out),
                        "level": level,
                        "bucket": bucket,
                        "difficulty": round(buckets[bucket], 3),
                        **self._one(bucket),
                    }
                )
        return out

    def score_session(
        self, by_id: dict[Any, dict[str, Any]], results: list, start_level: int
    ) -> dict[str, int]:
        """Authoritative scoring of a finished session.

        The default validates each submitted answer in play order and replays
        the level/streak rules over the outcomes (see ``levels.py``).
        Self-scored games override this with their own replay. Returns
        ``{"score", "level", "correct"}``.
        """
        outcomes = []
        for item in results:
            activity = by_id.get(item.id)
            if activity is None:
                continue
            outcomes.append(self.validate(activity, item.answer))
        played = replay(outcomes, start_level)
        return {**played, "correct": sum(outcomes)}

    def meta(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "kind": self.kind,
            "advanced": self.advanced,
            "self_scored": self.self_scored,
            # Games that bundle their own dynamics are imported from here by
            # the frontend; base kinds load frontend/js/games/<kind>.js instead.
            "renderer_url": (
                f"/api/games/{self.key}/renderer.js" if self.renderer_path else None
            ),
            # Quota mode (quiz_count > 0) replaces the countdown entirely.
            "timed": self.timed and not config.QUIZZES_PER_GAME,
            "duration_seconds": self.duration_seconds,
            "quiz_count": config.QUIZZES_PER_GAME,
            "max_errors": self.max_errors,
        }


class ChoiceGame(Game):
    """A game whose activities are 'tap the right option among several'."""

    kind = "choice"
    calibrated = True  # clean per-answer success/failure signal to learn from

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        try:
            return int(answer) == int(activity["answer"])
        except (TypeError, ValueError, KeyError):
            return False
