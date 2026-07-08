"""'Conta e abbina' – count the objects and pick the group of the same size.

Fully procedural and wordless: a group of objects is shown (e.g. 🍎🍎🍎) and
the child taps, among groups of a *different* object, the one with the same
amount. Difficulty comes from two parameters: the size of the count (2–3 can
be subitized at a glance, 4–6 needs real counting) and how close the wrong
amounts sit to the right one (±1 is confusable, far counts are easy to
reject).
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

# Single-codepoint emojis only, so an option is simply the symbol repeated N
# times (and tests can count symbols with len()).
ITEMS = ["🍎", "🐟", "🔵", "⭐", "🎈", "🐤", "🌸", "🍪", "🐞", "🦆"]

RANGES = {"small": (2, 3), "big": (4, 6)}


class CountGame(ChoiceGame):
    key = "count"
    name = "Conta e abbina"
    icon = "🔢"
    color = "#E8A33D"

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "small/far": 0.18,
            "small/near": 0.42,
            "big/far": 0.55,
            "big/near": 0.82,
        }

    def _one(self, bucket: str) -> dict[str, Any]:
        size, prox = bucket.split("/")
        lo, hi = RANGES[size]
        n = random.randint(lo, hi)
        shown, answer_item = random.sample(ITEMS, 2)

        if prox == "near":
            wrong = [c for c in (n - 1, n + 1) if c >= 1]
        else:
            wrong = [c for c in range(1, hi + 3) if abs(c - n) >= 2]
        counts = [n] + random.sample(wrong, 2)
        random.shuffle(counts)

        return {
            "kind": "choice",
            "stimulus": [shown] * n,
            "options": [answer_item * c for c in counts],
            "answer": counts.index(n),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": ["🍎", "🍎"],
            "options": ["🐟", "🐟🐟", "🐟🐟🐟"],
            "answer": 1,
        }
