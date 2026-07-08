"""'Cosa va insieme?' – pick the item that belongs with the cue.

A single stimulus (e.g. 🐝) is shown; the child taps, among the options, the
object that goes with it (🍯).

Only *partially* procedural: the associations themselves encode world knowledge
and are curated by hand. What we generate procedurally is the **difficulty** —
by choosing distractors from the same family as the answer (near, confusable)
or from unrelated families (far), and by widening the option count. Those two
parameters form the difficulty bucket.
"""
from __future__ import annotations

import random
from typing import Any

from ..base import ChoiceGame

# (cue, matching item, family). The family groups matches that are "the same
# kind of thing", so same-family distractors are the confusable ones.
PAIRS = [
    ("🐝", "🍯", "animal_food"),
    ("🐔", "🥚", "animal_food"),
    ("🐭", "🧀", "animal_food"),
    ("🐰", "🥕", "animal_food"),
    ("🐵", "🍌", "animal_food"),
    ("🐶", "🦴", "animal_food"),
    ("🐿️", "🌰", "animal_food"),
    ("🐼", "🎋", "animal_food"),
    ("🐛", "🦋", "transform"),
    ("🕷️", "🕸️", "transform"),
    ("🌱", "🌳", "transform"),
    ("🥚", "🐣", "transform"),
    ("🐧", "🧊", "habitat"),
    ("🐫", "🌵", "habitat"),
    ("🐠", "🌊", "habitat"),
    ("🐒", "🌴", "habitat"),
    ("🌧️", "☔", "weather"),
    ("☀️", "🕶️", "weather"),
    ("❄️", "⛄", "weather"),
    ("🔑", "🔒", "object_pair"),
    ("✋", "🧤", "object_pair"),
    ("🦶", "🧦", "object_pair"),
    ("🖌️", "🎨", "object_pair"),
]


class PairsGame(ChoiceGame):
    key = "pairs"
    name = "Cosa va insieme?"
    icon = "🧩"
    color = "#9B59B6"

    def difficulty_buckets(self) -> dict[str, float]:
        return {
            "far/opt3": 0.25,
            "far/opt4": 0.40,
            "near/opt3": 0.58,
            "near/opt4": 0.72,
        }

    def _one(self, bucket: str) -> dict[str, Any]:
        prox, opt = bucket.split("/")
        near = prox == "near"
        n = int(opt[3:])                        # "opt4" -> 4

        cue, match, family = random.choice(PAIRS)
        exclude = {match, cue}                  # never offer the answer twice or the cue itself
        if near:
            pool = [m for _, m, f in PAIRS if f == family and m not in exclude]
        else:
            pool = [m for _, m, f in PAIRS if f != family and m not in exclude]
        # Top up if a family is too small to fill the requested option count.
        if len(pool) < n - 1:
            pool += [m for _, m, _ in PAIRS if m not in exclude and m not in pool]

        distractors = random.sample(pool, n - 1)
        options = [match] + distractors
        random.shuffle(options)
        return {
            "kind": "choice",
            "stimulus": [cue],
            "options": options,
            "answer": options.index(match),
        }

    def tutorial(self) -> dict[str, Any]:
        return {
            "id": "t",
            "kind": "choice",
            "stimulus": ["🐝"],
            "options": ["🦴", "🍯", "🥕"],
            "answer": 1,
        }
