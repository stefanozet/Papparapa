"""FastAPI application entry point.

Serves the JSON API under ``/api`` and the static frontend at ``/``.
Run with::

    uvicorn app.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models  # noqa: F401 (ensure models are imported for create_all)
from .config import FRONTEND_DIR
from .database import Base, engine
from .routers import auth, games, profiles

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Papparapa", description="Logic games for kids")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(profiles.router, prefix="/api")
app.include_router(games.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}


# The frontend is mounted last so that /api/* routes take precedence.
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
