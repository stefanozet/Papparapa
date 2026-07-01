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
    timed: bool
    duration_seconds: int
    max_errors: int


class StartOut(BaseModel):
    session_id: int
    game: GameMeta
    tutorial: dict[str, Any]
    activities: list[dict[str, Any]]


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


class StatsOut(BaseModel):
    total_score: int
    plays: int
    games: dict[str, dict[str, int]]
