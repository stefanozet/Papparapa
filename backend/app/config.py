"""Application configuration (all values overridable via environment)."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend
PROJECT_ROOT = BASE_DIR.parent                             # repository root
FRONTEND_DIR = PROJECT_ROOT / "frontend"

DATABASE_URL = os.getenv(
    "PAPPARAPA_DATABASE_URL", f"sqlite:///{BASE_DIR / 'papparapa.db'}"
)
SECRET_KEY = os.getenv("PAPPARAPA_SECRET_KEY", "dev-secret-change-me")
TOKEN_TTL_SECONDS = int(os.getenv("PAPPARAPA_TOKEN_TTL", str(60 * 60 * 24 * 30)))

# Points awarded for each correctly solved micro-activity.
POINTS_PER_ACTIVITY = int(os.getenv("PAPPARAPA_POINTS", "10"))

# Quizzes per game: when > 0 the countdown disappears and each game ends after
# this many quizzes instead. Set to 0 to bring the timer back.
QUIZZES_PER_GAME = int(os.getenv("PAPPARAPA_QUIZZES_PER_GAME", "5"))
