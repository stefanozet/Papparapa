"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ParentOut(BaseModel):
    id: int
    email: EmailStr

    model_config = {"from_attributes": True}


class ChildIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    avatar: str = Field(default="🐻", max_length=8)


class ChildOut(BaseModel):
    id: int
    name: str
    avatar: str

    model_config = {"from_attributes": True}


class GameMeta(BaseModel):
    key: str
    name: str
    icon: str
    color: str
    kind: str                   # interaction the frontend renders (choice, maze, ...)
    renderer_url: str | None = None  # set → the game bundles its own renderer.js
    advanced: bool = False      # own menu page; score outside ⭐ totals/leaderboard
    self_scored: bool = False   # the game awards its own points (no hearts/levels)
    timed: bool
    duration_seconds: int
    quiz_count: int             # > 0 → no countdown, the game ends after N quizzes
    max_errors: int


class StartOut(BaseModel):
    session_id: int
    game: GameMeta
    tutorial: dict[str, Any]
    activities: list[dict[str, Any]]
    start_level: int = 1        # the child resumes from their best level


class ResultItem(BaseModel):
    id: Any
    answer: Any


class FinishIn(BaseModel):
    results: list[ResultItem] = []
    errors: int = 0
    ended_reason: str = "completed"


class FinishOut(BaseModel):
    session_id: int
    score: int
    correct_count: int
    errors: int
    ended_reason: str
    level: int = 1              # level reached in this session
    max_level: int = 1          # best level ever, persisted per child+game


class StatsOut(BaseModel):
    total_score: int
    plays: int
    games: dict[str, dict[str, int]]


class LeaderboardEntry(BaseModel):
    child_id: int
    name: str
    avatar: str
    total_score: int
