"""'Completa la sequenza' – pick the item that continues the pattern.

Fully procedural: the *pattern type* is the generation parameter, and its
intrinsic regularity is the difficulty prior. Harder patterns also get a fourth
option to widen the choice.
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

FRUITS = ["🍎", "🍌", "🍇", "🍓", "🍊", "🍉", "🍐", "🥝", "🍑", "🍒"]
BALLS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
FACES = ["😀", "😎", "🥳", "😴", "😍", "🤩", "😇", "🤠"]
SHAPES = ["⭐", "❤️", "🔶", "🔷", "🟩", "🟥", "🔺", "🟢"]
ANIMALS = ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🦁"]
VEHICLES = ["🚗", "🚕", "🚌", "🚑", "🚒", "🚜", "🏎️", "🚓"]
POOLS = [FRUITS, BALLS, FACES, SHAPES, ANIMALS, VEHICLES]

# pattern name -> (unit builder, distinct symbols, parametric difficulty).
# More symbols and less regular repetition make a pattern harder to continue.
PATTERNS: dict[str, tuple[Any, int, float]] = {
    "AB": (lambda s: [s[0], s[1]], 2, 0.12),
    "AAB": (lambda s: [s[0], s[0], s[1]], 2, 0.30),
    "ABB": (lambda s: [s[0], s[1], s[1]], 2, 0.33),
    "ABC": (lambda s: [s[0], s[1], s[2]], 3, 0.50),
    "AABB": (lambda s: [s[0], s[0], s[1], s[1]], 2, 0.62),
    "ABCB": (lambda s: [s[0], s[1], s[2], s[1]], 3, 0.72),
    "ABCD": (lambda s: [s[0], s[1], s[2], s[3]], 4, 0.90),
}


class SequenceGame(ChoiceGame):
    key = "sequence"
    name = "Completa la sequenza"
    icon = "🔁"
    color = "#5B8DEF"

    def difficulty_buckets(self) -> dict[str, float]:
        return {name: w for name, (_, _, w) in PATTERNS.items()}

    def _one(self, bucket: str) -> dict[str, Any]:
        build, n_symbols, w = PATTERNS[bucket]
        pool = random.choice(POOLS)
        symbols = random.sample(pool, n_symbols)
        unit = build(symbols)

        # Vary how much of the pattern is visible: a random number of full
        # repeats plus a random partial repeat at the end. The cut point moves
        # the missing item to any position of the unit, so always answering
        # with the first symbol of the sequence no longer works.
        repeats = 2 if len(unit) >= 4 else random.choice([2, 3])
        cut = random.randrange(len(unit))
        shown = unit * repeats + unit[:cut]
        correct = unit[cut]                     # the item that comes next

        n_options = 4 if w >= 0.5 else 3        # harder patterns widen the choice
        distractors = [x for x in dict.fromkeys(symbols + pool) if x != correct]
        random.shuffle(distractors)
        options = [correct] + distractors[: n_options - 1]
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": shown + ["❓"],
            "options": options,
            "answer": options.index(correct),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": ["🔴", "🟡", "🔴", "🟡", "🔴", "❓"],
            "options": ["🟢", "🟡", "🔴"],
            "answer": 1,
        }
