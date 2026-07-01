"""Abstract game definitions.

Every game produces an ordered list of *micro-activities* of the same type.
The frontend engine plays them one after another under a time limit; reaching
``max_errors`` mistakes ends the game.  To add a new game, subclass ``Game``
(or ``ChoiceGame``) and register it in ``registry.py`` — nothing else needs to
change on the backend, and the frontend only needs a matching renderer.

Activity dict shapes
--------------------
choice : ``{"id": int, "kind": "choice", "stimulus": [str], "options": [str],
            "answer": int}``  – ``answer`` is the index of the correct option.
maze   : ``{"id": int, "kind": "maze", "grid": [str], "start": [r, c],
            "exit": [r, c]}``
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Game(ABC):
    key: str
    name: str
    icon: str                 # emoji shown in menus (visual, wordless)
    color: str                # theme color (hex)
    duration_seconds: int = 75
    activity_count: int = 20  # upper bound; the timer usually ends the game first
    max_errors: int = 3

    @abstractmethod
    def generate(self) -> list[dict[str, Any]]:
        """Return the ordered list of activity dicts (solutions included)."""

    @abstractmethod
    def tutorial(self) -> dict[str, Any]:
        """Return one simple sample activity for the wordless animated demo."""

    @abstractmethod
    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        """Return ``True`` when ``answer`` solves ``activity`` correctly."""

    def meta(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "icon": self.icon,
            "color": self.color,
            "duration_seconds": self.duration_seconds,
            "max_errors": self.max_errors,
        }


class ChoiceGame(Game):
    """A game whose activities are 'tap the right option among several'."""

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        try:
            return int(answer) == int(activity["answer"])
        except (TypeError, ValueError, KeyError):
            return False
