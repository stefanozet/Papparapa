"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Parent(Base):
    """A registered adult account. Children play under a parent account."""

    __tablename__ = "parents"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    children = relationship(
        "ChildProfile", back_populates="parent", cascade="all, delete-orphan"
    )


class ChildProfile(Base):
    """A child that plays. Identified visually by an avatar (no reading needed)."""

    __tablename__ = "child_profiles"

    id = Column(Integer, primary_key=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    avatar = Column(String, nullable=False, default="🐻")
    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("Parent", back_populates="children")
    sessions = relationship(
        "GameSession", back_populates="child", cascade="all, delete-orphan"
    )


class GameSession(Base):
    """One play-through of a single game by a child.

    ``spec`` stores the full generated game (including the solutions) so the
    server can validate the answers submitted at the end (anti-cheat for the
    choice games; the maze result is client-reported).
    """

    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True)
    child_id = Column(Integer, ForeignKey("child_profiles.id"), nullable=False, index=True)
    game_key = Column(String, nullable=False, index=True)
    spec = Column(JSON, nullable=False)
    status = Column(String, default="playing")          # playing | finished
    score = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    ended_reason = Column(String, nullable=True)        # completed | errors | timeout
    created_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    child = relationship("ChildProfile", back_populates="sessions")
