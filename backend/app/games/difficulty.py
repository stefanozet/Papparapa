"""Difficulty model shared by every game.

Two ingredients combine into the difficulty of a quiz:

* **Parametric prior** – a value in ``[0, 1]`` derived purely from the
  *parameters* used to build the quiz (pattern complexity, category
  similarity, maze size, …). Procedurally generated games expose these through
  ``Game.difficulty_buckets()``: a *bucket* is a compact signature of the
  generation parameters, and its prior is how hard those parameters *should*
  be. This is the link the spec asks for: "lo score deve essere legato ai
  parametri del processo di creazione del quiz".

* **Empirical evidence** – how children actually fared on that bucket. Every
  answered activity updates a per-bucket ``attempts``/``failures`` counter (see
  ``models.ActivityStat``). The observed failure rate is the empirical
  difficulty.

``blend`` fuses the two with Bayesian shrinkage so a bucket with little data
stays close to its prior and only drifts toward the measured failure rate as
evidence accumulates.
"""
from __future__ import annotations


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def blend(prior: float, attempts: int, failures: int, k: float = 8.0) -> float:
    """Shrink the empirical failure rate toward ``prior``.

    ``k`` is the prior's strength in pseudo-attempts. With no attempts the
    result is exactly ``prior``; with ``attempts >> k`` it approaches
    ``failures / attempts``.
    """
    if attempts <= 0:
        return clamp01(prior)
    return clamp01((prior * k + failures) / (k + attempts))


def stars(difficulty: float, n: int = 5) -> int:
    """Map a difficulty in ``[0, 1]`` onto ``1..n`` stars."""
    return max(1, min(n, round(clamp01(difficulty) * (n - 1)) + 1))


def ramp(count: int, lo: float, hi: float) -> list[float]:
    """``count`` target difficulties rising evenly from ``lo`` to ``hi``.

    Games walk this ramp to serve an easy → hard progression within a run.
    """
    if count <= 1:
        return [(lo + hi) / 2]
    return [lo + (hi - lo) * i / (count - 1) for i in range(count)]


def nearest_bucket(target: float, buckets: dict[str, float]) -> str:
    """The bucket whose prior difficulty is closest to ``target``."""
    return min(buckets.items(), key=lambda kv: abs(kv[1] - target))[0]
