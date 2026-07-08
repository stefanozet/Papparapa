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
    by_key = {g["key"]: g for g in data["games"]}
    assert {"sequence", "odd", "pairs", "count", "color", "memory", "memo", "simon", "maze"} <= set(by_key)
    # The menu lists the easiest games first (calibrated difficulty).
    diffs = [g["difficulty"] for g in data["games"]]
    assert diffs == sorted(diffs)
    # Default config is quota mode: no countdown, 5 quizzes per game.
    for key in ("sequence", "odd", "pairs", "count", "color", "memory", "memo", "simon", "maze"):
        assert by_key[key]["timed"] is False
        assert by_key[key]["quiz_count"] == 5
    # Every game tells the frontend how to render it: a base kind (the module
    # frontend/js/games/<kind>.js) or a bundled renderer served by the API.
    assert by_key["sequence"]["kind"] == "choice"
    assert by_key["maze"]["kind"] == "maze"
    for g in data["games"]:
        assert g["kind"]
        if not g["advanced"]:
            assert g["renderer_url"] is None    # base games all use base kinds


def test_bundled_asset_route():
    # Entangled is a folder game: its renderer and local imports are served.
    r = client.get("/api/games/entangled/renderer.js")
    assert r.status_code == 200 and "renderActivity" in r.text
    assert "javascript" in r.headers["content-type"]
    assert client.get("/api/games/entangled/logic.js").status_code == 200
    # Nothing else is: single-file games have no bundle, and only flat .js
    # files inside the game's own folder can ever be requested.
    assert client.get("/api/games/maze/renderer.js").status_code == 404
    assert client.get("/api/games/nope/renderer.js").status_code == 404
    assert client.get("/api/games/entangled/game.py").status_code == 404
    assert client.get("/api/games/entangled/missing.js").status_code == 404
    assert client.get("/api/games/entangled/..%2Flogic.js").status_code == 404


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

    # Answer every activity correctly: levels and streak bonuses beat the
    # flat 10-points-per-answer baseline, and the whole ladder is climbed.
    results = [{"id": a["id"], "answer": a["answer"]} for a in activities]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == len(activities)
    assert finish["score"] > len(activities) * 10
    assert finish["level"] == 10
    assert finish["max_level"] == 10

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
    assert finish["level"] == 1                  # no points, no level-up


def test_pairs_play_through(auth_headers):
    child = client.post(
        "/api/profiles", json={"name": "Gio", "avatar": "🐵"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/pairs/start?child_id={child['id']}", headers=auth_headers
    ).json()
    activities = start["activities"]
    assert activities and all(a["kind"] == "choice" for a in activities)
    # Each activity shows a single cue and 3–4 options (difficulty-dependent).
    assert all(len(a["stimulus"]) == 1 and 3 <= len(a["options"]) <= 4 for a in activities)

    results = [{"id": a["id"], "answer": a["answer"]} for a in activities]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == len(activities)
    assert finish["score"] >= len(activities) * 10


def test_count_correct_option_matches_the_quantity():
    """Exactly one option shows as many symbols as the cue — the answer."""
    game = GAMES["count"]
    for act in game.generate():
        n = len(act["stimulus"])
        assert len(set(act["stimulus"])) == 1          # one object type to count
        sizes = [len(opt) for opt in act["options"]]   # single-codepoint emojis
        assert sizes[act["answer"]] == n
        assert sizes.count(n) == 1                     # every distractor differs


def test_memory_answer_was_shown_and_distractors_were_not():
    game = GAMES["memory"]
    for act in game.generate():
        assert act["kind"] == "memory"
        assert act["peek_ms"] > 0
        shown = set(act["stimulus"])
        for i, option in enumerate(act["options"]):
            if i == act["answer"]:
                assert option in shown
            else:
                assert option not in shown


def test_memory_play_through(auth_headers):
    """The new "memory" kind is still validated server-side like any choice."""
    child = client.post(
        "/api/profiles", json={"name": "Nina", "avatar": "🦄"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/memory/start?child_id={child['id']}", headers=auth_headers
    ).json()
    activities = start["activities"]
    assert activities and all(a["kind"] == "memory" for a in activities)

    results = [{"id": a["id"], "answer": a["answer"]} for a in activities]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == len(activities)
    assert finish["score"] >= len(activities) * 10


def test_color_answer_matches_the_cue_and_distractors_do_not():
    from app.games.catalog.color import DOTS, OBJECTS

    colour_of_dot = {dot: colour for colour, dot in DOTS.items()}
    game = GAMES["color"]
    for act in game.generate():
        colour = colour_of_dot[act["stimulus"][0]]
        for i, option in enumerate(act["options"]):
            if i == act["answer"]:
                assert option in OBJECTS[colour]
            else:
                assert option not in OBJECTS[colour]


def test_memo_boards_are_made_of_pairs():
    from collections import Counter

    game = GAMES["memo"]
    for act in game.generate():
        assert act["kind"] == "memo"
        assert all(n == 2 for n in Counter(act["cards"]).values())
        # Each board carries its own error budget: one wrong pair per pair.
        assert act["max_errors"] == len(act["cards"]) // 2
    # Client-reported result, like the maze; no per-answer signal to calibrate.
    assert game.validate({}, {"solved": True}) is True
    assert game.validate({}, {"solved": False}) is False
    assert game.calibrated is False


def test_simon_sequences_are_replayable():
    game = GAMES["simon"]
    assert game.calibrated is True
    for act in game.generate():
        pads, seq = act["pads"], act["sequence"]
        assert all(0 <= i < len(pads) for i in seq)
        # No double flash: consecutive steps always differ.
        assert all(a != b for a, b in zip(seq, seq[1:]))
        assert game.validate(act, list(seq)) is True
        assert game.validate(act, seq[:-1]) is False      # stopped too early
        assert game.validate(act, None) is False


def test_simon_play_through(auth_headers):
    """The taps list is validated server-side against the sequence."""
    child = client.post(
        "/api/profiles", json={"name": "Tom", "avatar": "🐢"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/simon/start?child_id={child['id']}", headers=auth_headers
    ).json()
    activities = start["activities"]
    assert activities and all(a["kind"] == "simon" for a in activities)

    results = [{"id": a["id"], "answer": a["sequence"]} for a in activities]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["correct_count"] == len(activities)
    assert finish["score"] >= len(activities) * 10


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


def test_leaderboard(auth_headers):
    assert client.get("/api/leaderboard").status_code in (401, 403)

    child = client.post(
        "/api/profiles", json={"name": "Zoe", "avatar": "🐙"}, headers=auth_headers
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

    board = client.get("/api/leaderboard", headers=auth_headers).json()
    scores = [e["total_score"] for e in board]
    assert scores == sorted(scores, reverse=True)      # best first
    mine = next(e for e in board if e["child_id"] == child["id"])
    assert mine["name"] == "Zoe" and mine["total_score"] > 0
    # Children who never played are still on the board, with 0 points.
    idle = client.post(
        "/api/profiles", json={"name": "Ugo", "avatar": "🐳"}, headers=auth_headers
    ).json()
    board = client.get("/api/leaderboard", headers=auth_headers).json()
    assert any(e["child_id"] == idle["id"] and e["total_score"] == 0 for e in board)


# --------------------------------------------------------------------------- #
# Levels, multipliers and streak bonuses
# --------------------------------------------------------------------------- #
def test_level_math():
    from app.games.levels import points_for, replay, streak_bonus, threshold_for

    # Points per correct answer: base 10 times 1.5 per level, floored.
    assert [points_for(lv) for lv in (1, 2, 3, 4, 10)] == [10, 15, 22, 33, 384]
    # Clearing a level takes 3 correct answers' worth of points.
    assert threshold_for(1) == 30 and threshold_for(2) == 45

    # Fibonacci streak bonuses: the 3rd correct in a row earns +1, then every
    # streak equal to 3 + fib (4, 5, 6, 8, 11, 16, ...) earns index + 1.
    expected = {1: 0, 2: 0, 3: 1, 4: 1, 5: 2, 6: 3, 7: 0, 8: 4, 9: 0, 11: 5, 16: 6}
    for streak, bonus in expected.items():
        assert streak_bonus(streak) == bonus, streak

    # Four straight correct answers from level 1: 10 + 10 + (10+1) clears the
    # level (31 >= 30); the 4th is worth 15 + 1 (streak of 4) at level 2.
    assert replay([True, True, True, True], start_level=1) == {"score": 47, "level": 2}
    # A mistake resets the streak but not the points already put into a level.
    assert replay([True, True, False, True], start_level=1) == {"score": 30, "level": 2}
    # Levels are capped at 10.
    assert replay([True] * 50, start_level=10)["level"] == 10


def test_levels_persist_and_resume(auth_headers):
    child = client.post(
        "/api/profiles", json={"name": "Lia", "avatar": "🐨"}, headers=auth_headers
    ).json()

    # First run starts at level 1 and offers batches for every level up to 10.
    start = client.post(
        f"/api/games/sequence/start?child_id={child['id']}", headers=auth_headers
    ).json()
    assert start["start_level"] == 1
    assert {a["level"] for a in start["activities"]} == set(range(1, 11))

    # Six straight correct answers clear levels 1 and 2 (score 82, level 3).
    picked = start["activities"][:6]
    results = [{"id": a["id"], "answer": a["answer"]} for a in picked]
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 0, "ended_reason": "timeout"},
        headers=auth_headers,
    ).json()
    assert finish["score"] == 82
    assert finish["level"] == 3
    assert finish["max_level"] == 3

    # The next run resumes from the best level: no easier batches on offer.
    again = client.post(
        f"/api/games/sequence/start?child_id={child['id']}", headers=auth_headers
    ).json()
    assert again["start_level"] == 3
    assert min(a["level"] for a in again["activities"]) == 3

    # A bad run never lowers the stored best level.
    bad = [
        {"id": a["id"], "answer": (a["answer"] + 1) % len(a["options"])}
        for a in again["activities"][:3]
    ]
    finish = client.post(
        f"/api/sessions/{again['session_id']}/finish",
        json={"results": bad, "errors": 3, "ended_reason": "errors"},
        headers=auth_headers,
    ).json()
    assert finish["level"] == 3 and finish["max_level"] == 3
    third = client.post(
        f"/api/games/sequence/start?child_id={child['id']}", headers=auth_headers
    ).json()
    assert third["start_level"] == 3


# --------------------------------------------------------------------------- #
# Run planner
# --------------------------------------------------------------------------- #
def test_planner_orders_easy_first_and_replays_harder():
    from app.games.planner import REPLAY_COUNT, REPLAY_LEVEL_DELTA, plan_run

    # Difficulty gaps wider than twice the jitter make the order deterministic.
    diffs = {"hard": 0.9, "easy": 0.1, "mid": 0.5}
    plan = plan_run(diffs)
    assert [e["key"] for e in plan[:3]] == ["easy", "mid", "hard"]
    assert all(e["level_delta"] == 0 for e in plan[:3])
    # The easiest games return as the finale, one notch harder.
    tail = plan[3:]
    assert [e["key"] for e in tail] == ["easy", "mid"][:REPLAY_COUNT]
    assert all(e["level_delta"] == REPLAY_LEVEL_DELTA for e in tail)


def test_run_plan_endpoint(auth_headers):
    assert client.get("/api/runs/plan?child_id=1").status_code in (401, 403)

    child = client.post(
        "/api/profiles", json={"name": "Pia", "avatar": "🐝"}, headers=auth_headers
    ).json()
    plan = client.get(
        f"/api/runs/plan?child_id={child['id']}", headers=auth_headers
    ).json()["plan"]

    # Every base game is proposed once (advanced games stay out of the
    # partita), then the harder re-proposals close the run.
    base = {k for k, g in GAMES.items() if not g.advanced}
    keys = [e["key"] for e in plan]
    assert set(keys[: len(base)]) == base
    assert all(e["level_delta"] == 0 for e in plan[: len(base)])
    replays = plan[len(base):]
    assert replays, "the plan re-proposes some games in a harder mode"
    assert all(e["level_delta"] > 0 for e in replays)
    assert set(e["key"] for e in replays) <= base


def test_level_delta_starts_harder(auth_headers):
    child = client.post(
        "/api/profiles", json={"name": "Ivo", "avatar": "🦖"}, headers=auth_headers
    ).json()
    # A fresh child re-proposed at +2 starts from level 3, batches included.
    start = client.post(
        f"/api/games/sequence/start?child_id={child['id']}&level_delta=2",
        headers=auth_headers,
    ).json()
    assert start["start_level"] == 3
    assert min(a["level"] for a in start["activities"]) == 3
    # The delta is capped at the top of the ladder...
    capped = client.post(
        f"/api/games/sequence/start?child_id={child['id']}&level_delta=99",
        headers=auth_headers,
    ).json()
    assert capped["start_level"] == 10
    # ...and can never make a game easier than the child's stored level.
    negative = client.post(
        f"/api/games/sequence/start?child_id={child['id']}&level_delta=-5",
        headers=auth_headers,
    ).json()
    assert negative["start_level"] == 1


# --------------------------------------------------------------------------- #
# Procedural generation & difficulty model
# --------------------------------------------------------------------------- #
def test_difficulty_math():
    from app.games.difficulty import blend, nearest_bucket, ramp, stars

    assert blend(0.5, 0, 0) == 0.5                 # no trials -> parametric prior
    assert blend(0.2, 100, 100) > 0.9             # all failures -> hard
    assert blend(0.8, 100, 0) < 0.1               # all successes -> easy
    assert stars(0.0) == 1 and stars(1.0) == 5
    r = ramp(5, 0.0, 1.0)
    assert r[0] == 0.0 and r[-1] == 1.0 and r == sorted(r)
    assert nearest_bucket(0.51, {"a": 0.1, "b": 0.5, "c": 0.9}) == "b"


def test_every_activity_carries_a_difficulty_bucket():
    for key, game in GAMES.items():
        buckets = game.difficulty_buckets()
        assert buckets, key
        acts = game.generate()
        assert acts, key
        for a in acts:
            assert a["bucket"] in buckets, (key, a["bucket"])
            assert 0.0 <= a["difficulty"] <= 1.0
            assert 1 <= a["level"] <= 10
        if game.advanced:
            continue        # advanced games play one board, no level ladder
        diffs = [a["difficulty"] for a in acts]
        assert diffs == sorted(diffs), key       # easy -> hard progression
        assert {a["level"] for a in acts} == set(range(1, 11)), key


def test_difficulty_endpoint_and_catalogue():
    report = client.get("/api/games/difficulty").json()["games"]
    for key in ("sequence", "odd", "pairs", "count", "color", "memory", "memo", "simon", "maze"):
        entry = report[key]
        assert 0.0 <= entry["difficulty"] <= 1.0
        assert 1 <= entry["stars"] <= 5
        assert entry["buckets"], key             # per-bucket breakdown present
    # The public catalogue surfaces the same difficulty for the menu.
    for g in client.get("/api/games").json()["games"]:
        assert 0.0 <= g["difficulty"] <= 1.0
        assert 1 <= g["stars"] <= 5


def test_trials_raise_measured_difficulty(auth_headers):
    before = client.get("/api/games/difficulty").json()["games"]["pairs"]["difficulty"]

    child = client.post(
        "/api/profiles", json={"name": "Cal", "avatar": "🦉"}, headers=auth_headers
    ).json()
    start = client.post(
        f"/api/games/pairs/start?child_id={child['id']}", headers=auth_headers
    ).json()
    acts = start["activities"]
    # Answer every activity WRONG so its buckets accrue failures.
    results = [
        {"id": a["id"], "answer": (a["answer"] + 1) % len(a["options"])} for a in acts
    ]
    client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": results, "errors": 3, "ended_reason": "errors"},
        headers=auth_headers,
    )

    after = client.get("/api/games/difficulty").json()["games"]["pairs"]
    assert after["attempts"] >= len(acts)
    assert after["difficulty"] > before          # failures push the score up


def test_maze_difficulty_is_parametric_only():
    # The maze has no clean per-answer failure signal, so it is not calibrated.
    assert GAMES["maze"].calibrated is False
    report = client.get("/api/games/difficulty").json()["games"]["maze"]
    assert report["calibrated"] is False


# --------------------------------------------------------------------------- #
# Entangled (advanced, self-scored, bundled renderer)
# --------------------------------------------------------------------------- #
def _straight_tile():
    """A tile whose lines all cross straight to the opposite side."""
    links = [0] * 12
    for i in range(6):
        links[2 * i] = 2 * ((i + 3) % 6) + 1
        links[2 * i + 1] = 2 * ((i + 3) % 6)
    return links


def test_entangled_is_advanced_and_bundled():
    game = GAMES["entangled"]
    assert game.advanced is True and game.self_scored is True
    meta = game.meta()
    assert meta["renderer_url"] == "/api/games/entangled/renderer.js"
    by_key = {g["key"]: g for g in client.get("/api/games").json()["games"]}
    assert by_key["entangled"]["advanced"] is True
    assert by_key["entangled"]["self_scored"] is True


def test_entangled_generation_invariants():
    acts = GAMES["entangled"].generate()
    assert len(acts) == 1                       # one whole board per session
    act = acts[0]
    assert 0 <= act["start"] < 12
    assert len(act["draws"]) == 37              # hand of 2 + refills for 36 cells
    for links in act["draws"]:
        assert sorted(links) == list(range(12))          # a permutation...
        assert all(links[links[a]] == a for a in range(12))   # ...an involution
        assert all(links[a] != a for a in range(12))     # ...with no fixed point


def test_entangled_simulation_rules():
    from app.games.catalog.entangled.game import fib, simulate

    straight = _straight_tile()
    draws = [straight] * 37
    # Straight tiles march the path from the centre to the border: 3 cells
    # (board radius), one crossing per move, fib(1) = 1 point each.
    out = simulate(0, draws, [{"choice": 0, "rotation": 0}] * 9)
    assert out == {"score": 3, "gains": [1, 1, 1], "moves_played": 3, "ended": "border"}
    # Fewer moves than needed leave the game pending, points still earned.
    out = simulate(0, draws, [{"choice": 0, "rotation": 0}])
    assert out["ended"] == "pending" and out["score"] == 1
    # Malformed moves stop the replay instead of crashing it.
    out = simulate(0, draws, [{"choice": 5}, {"choice": 0, "rotation": 0}])
    assert out == {"score": 0, "gains": [], "moves_played": 0, "ended": "pending"}
    assert [fib(n) for n in (0, 1, 2, 3, 4, 5)] == [0, 1, 1, 2, 3, 5]


def test_entangled_score_is_replayed_and_stays_out_of_totals(auth_headers):
    from app.games.catalog.entangled.game import simulate

    child = client.post(
        "/api/profiles", json={"name": "Rex", "avatar": "🦕"}, headers=auth_headers
    ).json()
    before = client.get(f"/api/profiles/{child['id']}/stats", headers=auth_headers).json()

    start = client.post(
        f"/api/games/entangled/start?child_id={child['id']}", headers=auth_headers
    ).json()
    act = start["activities"][0]
    assert start["game"]["kind"] == "entangled"

    # Play blindly and let the server tell the authoritative score.
    moves = [{"choice": 0, "rotation": 0}] * 40
    expected = simulate(act["start"], act["draws"], moves)
    finish = client.post(
        f"/api/sessions/{start['session_id']}/finish",
        json={"results": [{"id": act["id"], "answer": {"moves": moves}}],
              "errors": 0, "ended_reason": "completed"},
        headers=auth_headers,
    ).json()
    assert finish["score"] == expected["score"]
    assert finish["correct_count"] == expected["moves_played"]
    assert finish["level"] == 1                 # no ladder for advanced games

    # The personal best is recorded, but the ⭐ total ignores advanced games.
    stats = client.get(f"/api/profiles/{child['id']}/stats", headers=auth_headers).json()
    assert stats["games"]["entangled"]["best"] == expected["score"]
    assert stats["total_score"] == before["total_score"]
    board = client.get("/api/leaderboard", headers=auth_headers).json()
    mine = next(e for e in board if e["child_id"] == child["id"])
    assert mine["total_score"] == 0
