"""Run planner: which games a full partita proposes, and in what order.

The old hand-curated ``DEFAULT_RUN`` list is gone: the app decides the order
from each game's calibrated difficulty (see ``difficulty.py`` — the value
blends the parametric priors with how children actually fared).  The policy
lives in this one function so it can be iterated on without touching the API:

* every game appears once, easiest first, with a little random jitter so no
  two partite are identical;
* the ``REPLAY_COUNT`` easiest games come back at the end of the run with a
  positive ``level_delta`` — the same game, re-proposed in a harder mode
  (``start_game`` raises the starting level by that delta).
"""
from __future__ import annotations

import random

# Uniform noise added to each game's difficulty when ordering the run: enough
# to swap neighbours game-to-game, not enough to send a hard game first.
JITTER = 0.15
# How many games return at the end of the run, and how much harder they get.
REPLAY_COUNT = 2
REPLAY_LEVEL_DELTA = 2


def plan_run(
    difficulties: dict[str, float], rng: random.Random | None = None
) -> list[dict]:
    """Ordered plan for a full partita: ``[{"key", "level_delta"}, ...]``.

    ``difficulties`` maps each game key to its calibrated difficulty in
    ``[0, 1]``; ``rng`` is injectable for deterministic tests.
    """
    rng = rng or random.Random()
    order = sorted(
        difficulties, key=lambda k: difficulties[k] + rng.uniform(-JITTER, JITTER)
    )
    plan = [{"key": key, "level_delta": 0} for key in order]
    # The easiest games return as the finale, one notch harder each.
    for key in order[:REPLAY_COUNT]:
        plan.append({"key": key, "level_delta": REPLAY_LEVEL_DELTA})
    return plan
