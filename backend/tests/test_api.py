"""End-to-end API tests covering the full player journey."""
from __future__ import annotations

import os
import tempfile

import pytest

# Use a throwaway database file per test session.
_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["PAPPARAPA_DATABASE_URL"] = f"sqlite:///{_db_path}"

from fastapi.testclient import TestClient  # noqa: E402

from app.games import GAMES  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_headers():
    r = client.post(
        "/api/auth/register", json={"email": "p@example.com", "password": "secret1"}
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_duplicate_registration_rejected():
    client.post("/api/auth/register", json={"email": "dup@x.com", "password": "secret1"})
    r = client.post("/api/auth/register", json={"email": "dup@x.com", "password": "secret1"})
    assert r.status_code == 409


def test_login_wrong_password():
    client.post("/api/auth/register", json={"email": "log@x.com", "password": "secret1"})
    r = client.post("/api/auth/login", json={"email": "log@x.com", "password": "nope"})
    assert r.status_code == 401


def test_protected_route_requires_token():
    assert client.get("/api/profiles").status_code in (401, 403)


def test_game_catalogue():
    data = client.get("/api/games").json()
    keys = {g["key"] for g in data["games"]}
    assert {"sequence", "odd", "maze"} <= keys
    assert len(data["default_run"]) == 3


def test_full_play_through(auth_headers):
    # Create a child profile.
    child = client.post(
        "/api/profiles", json={"name": "Leo", "avatar": "🦊"}, headers=auth_headers
    ).json()

    # Start a sequence game.
    start = client.post(
        f"/api/games/sequence/start?child_id={child['id']}", headers=auth_headers
    ).json()
    activities = start["activities"]
    assert activities and all(a["kind"] == "choice" for a in activities)

    # Answer every activity correctly.
    results = [{"id": a["id"], "answer": a["answer"]} for a in activities]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == len(activities)
    assert finish["score"] == len(activities) * 10

    # Finishing twice is rejected.
    again = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": [], "errors": 0},
        headers=auth_headers,
    )
    assert again.status_code == 409


def test_wrong_answers_score_zero(auth_headers):
    child = client.post(
        "/api/profiles", json={"name": "Mia", "avatar": "🐰"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/odd/start?child_id={child['id']}", headers=auth_headers
    ).json()
    # Deliberately submit wrong answers.
    results = [
        {"id": a["id"], "answer": (a["answer"] + 1) % len(a["options"])}
        for a in start["activities"]
    ]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 3, "ended_reason": "errors"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == 0
    assert finish["score"] == 0


def test_maze_generation_is_solvable():
    """Every generated maze must have a path from start to exit (BFS)."""
    from collections import deque

    maze = GAMES["maze"]
    for act in maze.generate():
        grid, (sr, sc), (er, ec) = act["grid"], act["start"], act["exit"]
        seen = {(sr, sc)}
        q = deque([(sr, sc)])
        found = False
        while q:
            r, c = q.popleft()
            if (r, c) == (er, ec):
                found = True
                break
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if (
                    0 <= nr < len(grid)
                    and 0 <= nc < len(grid[0])
                    and grid[nr][nc] != "#"
                    and (nr, nc) not in seen
                ):
                    seen.add((nr, nc))
                    q.append((nr, nc))
        assert found, "maze is not solvable"


def test_stats_after_play(auth_headers):
    child = client.post(
        "/api/profiles", json={"name": "Sam", "avatar": "🐼"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/sequence/start?child_id={child['id']}", headers=auth_headers
    ).json()
    results = [{"id": a["id"], "answer": a["answer"]} for a in start["activities"]]
    client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0},
        headers=auth_headers,
    )
    stats = client.get(f"/api/profiles/{child['id']}/stats", headers=auth_headers).json()
    assert stats["plays"] == 1
    assert stats["total_score"] > 0
    assert "sequence" in stats["games"]
