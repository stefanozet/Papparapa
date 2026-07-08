"""'Memoria lampo' – memorise the group, then pick the item that was there.

The items flash on screen for a moment (``peek_ms``), get covered by ❓, and
the child taps, among the options, the one that was in the group. This is a
new activity ``kind`` ("memory"): after the peek the interaction is a plain
choice, so the frontend renderer masks the stimulus and delegates to the
choice renderer (see ``frontend/js/games/memory.js``).

Fully procedural difficulty on two axes: how many items must be held in
memory (the peek grows a little with the load), and whether the distractors
come from the same category as the seen items (near, confusable — "was it
this cat or that one?") or from different ones (far, easy to reject).
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

CATEGORIES = {
    "animals": ["🐶", "🐱", "🐭", "🐰", "🦊", "🐻", "🐼", "🦁"],
    "fruit": ["🍎", "🍌", "🍇", "🍓", "🍊", "🍉", "🍐", "🍒"],
    "vehicles": ["🚗", "🚌", "🚑", "🚒", "🚜", "🚓", "🚀", "🚁"],
    "clothes": ["👕", "👖", "🧢", "🧦", "👟", "🧤", "👒", "🧣"],
    "toys": ["⚽", "🎈", "🎁", "🧸", "🪁", "🥁", "🎨", "🪀"],
}


class MemoryGame(ChoiceGame):
    key = "memory"
    name = "Memoria lampo"
    icon = "🧠"
    color = "#D96BA0"
    kind = "memory"    # a choice quiz, but the stimulus is masked after peek_ms

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "n2/far": 0.20,
            "n3/far": 0.40,
            "n2/near": 0.55,
            "n3/near": 0.75,
            "n4/near": 0.90,
        }

    def _one(self, bucket: str) -> dict[str, Any]:
        size, prox = bucket.split("/")
        n = int(size[1:])                       # "n3" -> 3

        category = random.choice(list(CATEGORIES))
        shown = random.sample(CATEGORIES[category], n)
        answer = random.choice(shown)
        if prox == "near":
            pool = [x for x in CATEGORIES[category] if x not in shown]
        else:
            pool = [x for c, items in CATEGORIES.items() if c != category for x in items]

        options = [answer] + random.sample(pool, 2)
        random.shuffle(options)
        return {
            "kind": "memory",
            "peek_ms": 1200 + 400 * n,          # a bigger load earns a longer look
            "stimulus": shown,
            "options": options,
            "answer": options.index(answer),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "memory",
            "peek_ms": 2000,
            "stimulus": ["🐶", "🍎"],
            "options": ["🚗", "🐶", "🌵"],
            "answer": 1,
        }
