"""'Ripeti il ritmo' – watch the pads light up in order, then replay it.

A Simon-style game: a row of pads (drums, animals, …) flashes a sequence 👀
and the child taps the same pads in the same order 👆. A wrong tap costs a
heart. A new activity ``kind`` ("simon") with its own renderer
(``frontend/js/games/simon.js``).

Fully procedural difficulty on two axes: the length of the sequence to hold in
memory and how many pads there are to confuse. Unlike the maze/memo, replaying
a sequence has a clean per-activity success/failure signal, so the answer (the
list of taps) is validated server-side and the game is ``calibrated``.
"""
from __future__ import annotations

import random
from typing import Any

from ..base import Game

PAD_SETS = [
    ["🥁", "🎺", "🎸", "🎹"],
    ["🐶", "🐱", "🐸", "🐤"],
    ["🔔", "🎷", "🪘", "🎻"],
]


class SimonGame(Game):
    key = "simon"
    name = "Ripeti il ritmo"
    icon = "🥁"
    color = "#6BCB77"
    kind = "simon"
    calibrated = True       # exact-sequence replay is a clean signal to learn from

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "len2/pads3": 0.15,
            "len3/pads3": 0.38,
            "len3/pads4": 0.55,
            "len4/pads4": 0.75,
            "len5/pads4": 0.92,
        }

    def _one(self, bucket: str) -> dict[str, Any]:
        size, pad_b = bucket.split("/")
        length = int(size[len("len"):])         # "len4" -> 4
        n_pads = int(pad_b[len("pads"):])       # "pads3" -> 3

        pads = random.sample(random.choice(PAD_SETS), n_pads)
        sequence: list[int] = []
        while len(sequence) < length:
            i = random.randrange(n_pads)
            if sequence and sequence[-1] == i:
                continue                        # a double flash is hard to perceive
            sequence.append(i)
        return {"kind": "simon", "pads": pads, "sequence": sequence}

    def tutorial(self) -> dict[str, Any]:
        return {"id": "t", "kind": "simon", "pads": ["🥁", "🎺", "🎸"], "sequence": [0, 2]}

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        try:
            return [int(x) for x in answer] == list(activity["sequence"])
        except (TypeError, ValueError, KeyError):
            return False
