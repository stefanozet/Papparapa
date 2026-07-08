"""'Memo delle coppie' – flip the cards two at a time and find every pair.

The classic memory-cards game: a board of face-down cards, each picture twice.
One board is one micro-activity; clearing it scores the points. A new activity
``kind`` ("memo") with its own renderer (``frontend/js/games/memo.js``).

Mistakes are part of the mechanic, so wrong pairs don't draw on the game-wide
hearts: each board grants its own error budget of ``tiles / 2`` wrong pairs
(``max_errors`` on the activity), refreshed on every new board. Spending the
whole budget ends the game. There is still no clean per-answer success/failure
signal, so like the maze the result is client-reported and the difficulty
stays parametric only (``calibrated = False``): the board size (number of
pairs) is the generation parameter.
"""
from __future__ import annotations

import random
from typing import Any

from ..base import Game

FACES = ["🍎", "🐟", "🌸", "🎈", "🐶", "⭐", "🍌", "🐸", "🚗", "🧀", "🦋", "🍓"]


class MemoGame(Game):
    key = "memo"
    name = "Memo delle coppie"
    icon = "🃏"
    color = "#7E6BD9"
    kind = "memo"
    activities_per_level = 3  # boards are slow; the timer ends the game anyway

    def difficulty_buckets(self) -> dict[str, float]:
        return {"pairs2": 0.22, "pairs3": 0.52, "pairs4": 0.82}

    def _one(self, bucket: str) -> dict[str, Any]:
        pairs = int(bucket[len("pairs"):])      # "pairs3" -> 3
        cards = random.sample(FACES, pairs) * 2
        random.shuffle(cards)
        # Per-board error budget: as many wrong pairs as the board has pairs.
        return {"kind": "memo", "cards": cards, "max_errors": pairs}

    def tutorial(self) -> dict[str, Any]:
        return {"id": "t", "kind": "memo", "cards": ["🍎", "🐟", "🍎", "🐟"]}

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        if isinstance(answer, dict):
            return bool(answer.get("solved"))
        return bool(answer)
