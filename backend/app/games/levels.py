"""Level system shared by every game: 10 levels, multipliers, streak bonuses.

Levels
------
Every game has ``LEVEL_MAX`` (10) levels: level 1 plays the easiest generation
bucket, level 10 the hardest. ``Game.generate(start_level)`` maps each level
onto the bucket whose parametric difficulty is nearest to
``target_difficulty(level)`` and emits a batch of activities per level.

Points
------
A correct answer at level ``L`` is worth ``floor(base * 1.5 ** (L - 1))``
points — with the default base of 10: 10, 15, 22, 33, 50, 75, 113, 170, 256,
384.

Levelling up
------------
Points earned while at a level accumulate; reaching ``threshold_for(level)``
(``LEVEL_UP_ANSWERS`` correct answers' worth at that level) moves the player
up one level.

Streak bonuses (Fibonacci)
--------------------------
Consecutive correct answers earn bonus points on top. The 3rd in a row earns
+1; after that, a bonus lands on every streak equal to ``3 + fib(i)`` with
``fib = 1, 2, 3, 5, 8, 13, …`` and is worth ``i + 1`` points: streaks
3, 4, 5, 6, 8, 11, 16, 24 → +1, +1, +2, +3, +4, +5, +6, +7. A wrong answer
resets the streak (an unanswered activity does not).

The frontend mirrors these rules (``frontend/js/levels.js``) to drive the game
live; ``replay`` walks the submitted results in play order so the server's
score, like the answers themselves, stays authoritative.
"""
from __future__ import annotations

import math

from ..config import POINTS_PER_ACTIVITY

LEVEL_MAX = 10
LEVEL_UP_ANSWERS = 3    # correct answers' worth of points that clear a level
STREAK_START = 3        # streak length that earns the first bonus point


def points_for(level: int) -> int:
    """Points for one correct answer at ``level``."""
    return math.floor(POINTS_PER_ACTIVITY * 1.5 ** (level - 1))


def threshold_for(level: int) -> int:
    """Points to accumulate while at ``level`` to move up to the next one."""
    return LEVEL_UP_ANSWERS * points_for(level)


def target_difficulty(level: int) -> float:
    """Map a level onto the ``[0, 1]`` parametric difficulty scale."""
    return (level - 1) / (LEVEL_MAX - 1)


def streak_bonus(streak: int) -> int:
    """Bonus for the ``streak``-th consecutive correct answer (0 if none)."""
    if streak < STREAK_START:
        return 0
    if streak == STREAK_START:
        return 1
    fib, nxt = 1, 2
    index = 0
    while STREAK_START + fib <= streak:
        if STREAK_START + fib == streak:
            return index + 1
        fib, nxt = nxt, fib + nxt
        index += 1
    return 0


def replay(outcomes: list[bool], start_level: int) -> dict[str, int]:
    """Authoritative replay of a session.

    Walk the ordered answer outcomes applying points, streak bonuses and
    level-ups exactly as the frontend did live; return the final score and
    the level reached.
    """
    level = max(1, min(LEVEL_MAX, start_level))
    score = 0
    level_points = 0
    streak = 0
    for correct in outcomes:
        if not correct:
            streak = 0
            continue
        streak += 1
        gained = points_for(level) + streak_bonus(streak)
        score += gained
        level_points += gained
        if level < LEVEL_MAX and level_points >= threshold_for(level):
            level += 1
            level_points = 0
    return {"score": score, "level": level}
