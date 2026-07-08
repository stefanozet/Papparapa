"""Entangled: grow a path across a hexagonal board of random tiles.

Board & coordinates
-------------------
37 hexagonal cells (a hexagon of side 4) in axial coordinates ``(q, r)`` with
``max(|q|, |r|, |q + r|) <= RADIUS``. The centre ``(0, 0)`` holds the black
start tile; the other 36 cells receive tiles as the path grows.

Tiles & points
--------------
Every tile edge carries two points; the 12 points are indexed clockwise so
side ``i`` owns points ``2i`` and ``2i + 1``. A tile is a random perfect
matching of the 12 points (6 lines) stored as ``links``, an involution with
``links[a] = b``. Rotating a tile ``rot`` steps of 60° clockwise moves point
``a`` to ``(a + 2*rot) % 12``. Side ``i`` faces axial direction ``DIRS[i]``
(clockwise from East); adjacent tiles touch along opposite sides
(``j = (i + 3) % 6``) and the shared points meet mirrored, so exit point
``2i + o`` enters the neighbour at ``2j + (1 - o)``.

Play & scoring
--------------
The path starts from a random point of the centre tile. The player holds two
random tiles, may rotate the chosen one and places it on the cell the path
ends on; the path then follows the lines, chaining through every tile it
reaches (the same tile can be crossed again through different points). Each
move earns ``fib(k)`` points, ``k`` = tile crossings of that single move.
Placing consumes the chosen tile only: the other stays in hand and a fresh
one is drawn — the 37 pre-drawn tiles always cover the 36 placeable cells.
The game ends when the path leaves the board or returns to the centre tile.

The whole game is server-authoritative: the activity carries the start point
and every pre-drawn tile, the client submits only its moves
(``{"choice": 0|1, "rotation": 0..5}``) and ``score_session`` replays them.
``frontend`` counterpart: ``logic.js`` in this folder mirrors this module
exactly; keep the two in sync.
"""
from __future__ import annotations

import random
from typing import Any

from ...base import Game

RADIUS = 3
DIRS = [(1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]  # clockwise from E
HAND = 2           # tiles held by the player
TILES_TOTAL = 37   # hand + refills: one per placeable cell, plus one spare
FIB_CAP = 40       # safety cap on the fib index (unreachable in real play)


def fib(n: int) -> int:
    """Fibonacci with fib(1) = fib(2) = 1; fib(0) = 0."""
    n = max(0, min(n, FIB_CAP))
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def in_board(q: int, r: int) -> bool:
    return max(abs(q), abs(r), abs(q + r)) <= RADIUS


def random_tile(rng: random.Random) -> list[int]:
    """A random perfect matching of the 12 edge points."""
    points = list(range(12))
    rng.shuffle(points)
    links = [0] * 12
    for a, b in zip(points[::2], points[1::2]):
        links[a] = b
        links[b] = a
    return links


def rotated(links: list[int], rot: int) -> list[int]:
    """The tile's links after ``rot`` clockwise 60° steps."""
    out = [0] * 12
    for a in range(12):
        out[(a + 2 * rot) % 12] = (links[a] + 2 * rot) % 12
    return out


def mirror(p: int) -> int:
    """The neighbour's entry point matching exit point ``p``."""
    side, offset = divmod(p, 2)
    return 2 * ((side + 3) % 6) + (1 - offset)


def step(cell: tuple[int, int], p: int) -> tuple[tuple[int, int], int]:
    """Cross the edge at exit point ``p``: (neighbour cell, entry point)."""
    dq, dr = DIRS[p // 2]
    return (cell[0] + dq, cell[1] + dr), mirror(p)


def simulate(start: int, draws: list[list[int]], moves: list[Any]) -> dict[str, Any]:
    """Replay a whole game from its pre-drawn tiles and the player's moves.

    Malformed or impossible moves (bad indexes, game already over) stop the
    replay: the score is whatever was legitimately earned up to that point.
    Returns the final score, the per-move gains and how the game ended
    (``border`` / ``center`` / ``pending`` when moves ran out mid-game).
    """
    tiles: dict[tuple[int, int], list[int]] = {}
    hand: list[list[int] | None] = [draws[0], draws[1]]
    next_draw = HAND
    cell, entry = step((0, 0), start)   # the stub leaving the centre tile
    ended: str | None = None
    gains: list[int] = []
    for move in moves:
        if ended:
            break
        try:
            choice = int(move["choice"])
            rot = int(move.get("rotation", 0))
        except (TypeError, KeyError, ValueError):
            break
        if choice not in (0, 1) or not 0 <= rot < 6 or hand[choice] is None:
            break
        tiles[cell] = rotated(hand[choice], rot)
        hand[choice] = draws[next_draw] if next_draw < len(draws) else None
        next_draw += 1
        # Follow the path through every tile it reaches (chains included).
        crossings = 0
        while ended is None and cell in tiles:
            exit_p = tiles[cell][entry]
            crossings += 1
            cell, entry = step(cell, exit_p)
            if cell == (0, 0):
                ended = "center"
            elif not in_board(*cell):
                ended = "border"
        gains.append(fib(crossings))
    return {
        "score": sum(gains),
        "gains": gains,
        "moves_played": len(gains),
        "ended": ended or "pending",
    }


class EntangledGame(Game):
    key = "entangled"
    name = "Entangled"
    icon = "🧶"
    color = "#3E4A89"
    kind = "entangled"      # bundled renderer.js in this folder
    advanced = True         # own menu page, outside the partita and the ⭐ economy
    self_scored = True      # fib-per-move score, replayed by score_session
    timed = False           # one board, played to its natural end
    calibrated = False      # no per-answer signal to learn from

    def difficulty_buckets(self) -> dict[str, float]:
        # One fixed setup: the board is always the same, the tiles random.
        return {"standard": 0.75}

    def _one(self, bucket: str) -> dict[str, Any]:
        rng = random.Random()
        return {
            "kind": "entangled",
            "start": rng.randrange(12),
            "draws": [random_tile(rng) for _ in range(TILES_TOTAL)],
        }

    def generate(self, start_level: int = 1) -> list[dict[str, Any]]:
        # One whole board per session — no level ladder: the single activity
        # carries everything needed to play and to replay the game.
        return [
            {
                "id": 0,
                "level": 1,
                "bucket": "standard",
                "difficulty": 0.75,
                **self._one("standard"),
            }
        ]

    def tutorial(self) -> dict[str, Any]:
        return {"id": "t", **self._one("standard")}

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        # The answer is the move list; its worth is decided by the replay.
        return isinstance(answer, dict) and isinstance(answer.get("moves"), list)

    def score_session(self, by_id: dict, results: list, start_level: int) -> dict:
        score = 0
        moves_played = 0
        for item in results:
            activity = by_id.get(item.id)
            if activity is None or not self.validate(activity, item.answer):
                continue
            out = simulate(activity["start"], activity["draws"], item.answer["moves"])
            score += out["score"]
            moves_played += out["moves_played"]
        return {"score": score, "level": 1, "correct": moves_played}
