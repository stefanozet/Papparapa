"""'Trova l'intruso' – pick the item that does not belong with the others."""
from __future__ import annotations

import random
from typing import Any

from .base import ChoiceGame

CATEGORIES = {
    "fruit": ["🍎", "🍌", "🍇", "🍓", "🍊", "🍉", "🍐", "🍑"],
    "animal": ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🦁"],
    "vehicle": ["🚗", "🚕", "🚌", "🚑", "🚒", "🚜", "🏎️", "🚓"],
    "food": ["🍕", "🍔", "🌭", "🍟", "🍿", "🧀", "🥨", "🍩"],
    "nature": ["🌵", "🌲", "🌳", "🌻", "🌹", "🍄", "🌴", "🌷"],
}


class OddOneOutGame(ChoiceGame):
    key = "odd"
    name = "Trova l'intruso"
    icon = "🔍"
    color = "#E8734A"
    duration_seconds = 70

    def _one(self) -> dict[str, Any]:
        main_cat, other_cat = random.sample(list(CATEGORIES), 2)
        main = random.sample(CATEGORIES[main_cat], 3)
        intruder = random.choice(CATEGORIES[other_cat])
        options = main + [intruder]
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": [],
            "options": options,
            "answer": options.index(intruder),
        }

    def generate(self) -> list[dict[str, Any]]:
        return [{"id": i, **self._one()} for i in range(self.activity_count)]

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": [],
            "options": ["🍎", "🍌", "🚗", "🍇"],
            "answer": 2,
        }
