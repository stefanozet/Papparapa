"""'Stesso colore' – pick the object with the same colour as the cue dot.

A coloured dot is shown (e.g. 🔴) and the child taps, among the options, the
object of that colour (🍓). Association by a visual property rather than by
category or meaning.

Like "Cosa va insieme?" this is only *partially* procedural: which objects are
which colour is world knowledge curated by hand. The difficulty is generated —
distractors drawn from neighbouring colours (near: orange objects against a
red cue) or from distant ones (far), plus the option count.
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

DOTS = {
    "red": "🔴",
    "orange": "🟠",
    "yellow": "🟡",
    "green": "🟢",
    "blue": "🔵",
    "purple": "🟣",
    "brown": "🟤",
}

OBJECTS = {
    "red": ["🍎", "🍓", "🐞", "🌹", "🍒", "🍅"],
    "orange": ["🍊", "🥕", "🎃", "🦊", "🏀"],
    "yellow": ["🍌", "🌻", "🐤", "🧀", "🍋", "⭐"],
    "green": ["🐸", "🌵", "🍀", "🥦", "🐢", "🥒"],
    "blue": ["💧", "🐳", "🧊", "🦋", "👖"],
    "purple": ["🍇", "🍆", "🔮", "☂️"],
    "brown": ["🐻", "🌰", "🍫", "🥔", "🧸"],
}

# Colour pairs that sit close on the wheel: an orange object next to a red cue
# is easy to mistake, a green one is not.
NEAR = {
    frozenset({"red", "orange"}),
    frozenset({"orange", "yellow"}),
    frozenset({"orange", "brown"}),
    frozenset({"red", "brown"}),
    frozenset({"red", "purple"}),
    frozenset({"blue", "purple"}),
    frozenset({"green", "blue"}),
}


class ColorGame(ChoiceGame):
    key = "color"
    name = "Stesso colore"
    icon = "🎨"
    color = "#D64545"

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "far/opt3": 0.22,
            "far/opt4": 0.40,
            "near/opt3": 0.60,
            "near/opt4": 0.80,
        }

    def _one(self, bucket: str) -> dict[str, Any]:
        prox, opt = bucket.split("/")
        near = prox == "near"
        n = int(opt[3:])                        # "opt4" -> 4

        colour = random.choice(list(OBJECTS))
        answer = random.choice(OBJECTS[colour])
        others = [c for c in OBJECTS if c != colour]
        matching = [c for c in others if (frozenset({colour, c}) in NEAR) == near]
        pool = [obj for c in (matching or others) for obj in OBJECTS[c]]

        options = [answer] + random.sample(pool, n - 1)
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": [DOTS[colour]],
            "options": options,
            "answer": options.index(answer),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": ["🔴"],
            "options": ["🍌", "🍎", "🐸"],
            "answer": 1,
        }
