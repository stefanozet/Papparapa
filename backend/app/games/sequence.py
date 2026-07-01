"""'Completa la sequenza' – pick the item that continues the pattern."""
from __future__ import annotations

import random
from typing import Any

from .base import ChoiceGame

FRUITS = ["🍎", "🍌", "🍇", "🍓", "🍊", "🍉", "🍐", "🥝", "🍑", "🍒"]
BALLS = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣", "🟤", "⚫", "⚪"]
FACES = ["😀", "😎", "🥳", "😴", "😍", "🤩", "😇", "🤠"]
SHAPES = ["⭐", "❤️", "🔶", "🔷", "🟩", "🟥", "🔺", "🟢"]
POOLS = [FRUITS, BALLS, FACES, SHAPES]

# Repeating "units" that define a pattern.
UNIT_BUILDERS = {
    "AB": lambda s: [s[0], s[1]],
    "ABC": lambda s: [s[0], s[1], s[2]],
    "AAB": lambda s: [s[0], s[0], s[1]],
    "ABB": lambda s: [s[0], s[1], s[1]],
}
UNIT_SYMBOLS = {"AB": 2, "ABC": 3, "AAB": 2, "ABB": 2}


class SequenceGame(ChoiceGame):
    key = "sequence"
    name = "Completa la sequenza"
    icon = "🔁"
    color = "#5B8DEF"
    duration_seconds = 75

    def _one(self) -> dict[str, Any]:
        pool = random.choice(POOLS)
        kind = random.choice(list(UNIT_BUILDERS))
        symbols = random.sample(pool, UNIT_SYMBOLS[kind])
        unit = UNIT_BUILDERS[kind](symbols)

        shown = unit * 2                       # two full repeats, clearly visible
        correct = unit[len(shown) % len(unit)]  # the item that comes next

        distractors = [x for x in dict.fromkeys(unit + pool) if x != correct]
        random.shuffle(distractors)
        options = [correct] + distractors[:2]
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": shown + ["❓"],
            "options": options,
            "answer": options.index(correct),
        }

    def generate(self) -> list[dict[str, Any]]:
        return [{"id": i, **self._one()} for i in range(self.activity_count)]

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": ["🔴", "🟡", "🔴", "🟡", "❓"],
            "options": ["🟢", "🔴", "🟣"],
            "answer": 1,
        }
