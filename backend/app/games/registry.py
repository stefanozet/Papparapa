"""Registry of available games. Add new games here."""
from __future__ import annotations

from .base import Game
from .maze import MazeGame
from .odd_one_out import OddOneOutGame
from .sequence import SequenceGame

_GAME_CLASSES = [SequenceGame, OddOneOutGame, MazeGame]

GAMES: dict[str, Game] = {cls.key: cls() for cls in _GAME_CLASSES}

# Order in which the games are played in a full "run" (una partita completa).
DEFAULT_RUN = [SequenceGame.key, OddOneOutGame.key, MazeGame.key]
