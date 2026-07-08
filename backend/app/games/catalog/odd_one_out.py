"""'Trova l'intruso' – pick the item that does not belong with the others.

Procedural difficulty comes from two parameters: how *near* the intruder's
category is to the others (a near category is easy to mistake as belonging),
and how many options must be scanned (4 or 6).
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

CATEGORIES = {
    "fruit": ["🍎", "🍌", "🍇", "🍓", "🍊", "🍉", "🍐", "🍑", "🥝", "🍒"],
    "animal": ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🦁", "🐯", "🐨"],
    "vehicle": ["🚗", "🚕", "🚌", "🚑", "🚒", "🚜", "🏎️", "🚓", "🛵", "🚚"],
    "food": ["🍕", "🍔", "🌭", "🍟", "🍿", "🧀", "🥨", "🍩", "🥪", "🌮"],
    "nature": ["🌵", "🌲", "🌳", "🌻", "🌹", "🍄", "🌴", "🌷", "🌾", "🍁"],
    "sea": ["🐟", "🐠", "🐬", "🐙", "🦀", "🦑", "🐳", "🦈", "🐢", "🦞"],
    "sport": ["⚽", "🏀", "🏈", "🎾", "🏐", "🏉", "🎱", "🏓", "🏸", "🥎"],
}

# Category pairs that are easy to confuse (both living, both edible, …). When the
# intruder is drawn from a "near" category the odd one out is harder to spot.
NEAR = {
    frozenset({"fruit", "food"}),
    frozenset({"fruit", "nature"}),
    frozenset({"food", "nature"}),
    frozenset({"animal", "sea"}),
    frozenset({"animal", "nature"}),
    frozenset({"sea", "nature"}),
}


class OddOneOutGame(ChoiceGame):
    key = "odd"
    name = "Trova l'intruso"
    icon = "🔍"
    color = "#E8734A"

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "far/opt4": 0.30,
            "near/opt4": 0.52,
            "far/opt6": 0.55,
            "near/opt6": 0.78,
        }

    def _other_category(self, main: str, near: bool) -> str:
        others = [c for c in CATEGORIES if c != main]
        matching = [c for c in others if (frozenset({main, c}) in NEAR) == near]
        return random.choice(matching or others)

    def _one(self, bucket: str) -> dict[str, Any]:
        prox, opt = bucket.split("/")
        near = prox == "near"
        n = int(opt[3:])                        # "opt6" -> 6

        main_cat = random.choice(list(CATEGORIES))
        other_cat = self._other_category(main_cat, near)
        main = random.sample(CATEGORIES[main_cat], n - 1)
        intruder = random.choice(CATEGORIES[other_cat])
        options = main + [intruder]
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": [],
            "options": options,
            "answer": options.index(intruder),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": [],
            "options": ["🍎", "🍌", "🚗", "🍇"],
            "answer": 2,
        }
