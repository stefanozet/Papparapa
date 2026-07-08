"""'Il topo e il formaggio' – guide the mouse through the maze to the cheese.

Each maze is a micro-activity. Bumping into a wall costs a life; reaching the
cheese solves it. Mazes are perfect (single solution) mazes built with a
randomized depth-first search.

The maze result is client-reported (``{"solved": bool}``): there is no
incentive for a child to cheat, and validating a swipe path server-side would
add complexity without value. The choice games remain fully server-validated.
"""
from __future__ import annotations

import random
import sys
from typing import Any

from ..base import Game


# Grid size (in cells) is the generation parameter; a bigger maze means a
# longer path and more dead-ends, so size is the difficulty prior.
SIZE_DIFFICULTY = {2: 0.15, 3: 0.35, 4: 0.55, 5: 0.75, 6: 0.90}


class MazeGame(Game):
    key = "maze"
    name = "Il topo e il formaggio"
    icon = "🧀"
    color = "#3FA796"
    kind = "maze"
    timed = True           # 15s (shared default); bumping a wall still costs a heart
    activities_per_level = 4  # mazes are slow: a small batch per level is plenty

    def _maze(self, cells: int) -> dict[str, Any]:
        width = 2 * cells + 1
        grid = [["#"] * width for _ in range(width)]
        visited = [[False] * cells for _ in range(cells)]

        # Iterative randomized DFS (avoids recursion limits for large mazes).
        stack = [(0, 0)]
        visited[0][0] = True
        grid[1][1] = " "
        while stack:
            cy, cx = stack[-1]
            neighbours = []
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < cells and 0 <= nx < cells and not visited[ny][nx]:
                    neighbours.append((ny, nx, dy, dx))
            if not neighbours:
                stack.pop()
                continue
            ny, nx, dy, dx = random.choice(neighbours)
            visited[ny][nx] = True
            grid[2 * cy + 1 + dy][2 * cx + 1 + dx] = " "  # knock down the wall
            grid[2 * ny + 1][2 * nx + 1] = " "
            stack.append((ny, nx))

        return {
            "grid": ["".join(row) for row in grid],
            "start": [1, 1],
            "exit": [2 * cells - 1, 2 * cells - 1],
        }

    def difficulty_buckets(self) -> dict[str, float]:
        return {f"cells{n}": d for n, d in SIZE_DIFFICULTY.items()}

    def _one(self, bucket: str) -> dict[str, Any]:
        cells = int(bucket[len("cells"):])      # "cells4" -> 4
        return {"kind": "maze", **self._maze(cells)}

    def tutorial(self) -> dict[str, Any]:
        return {"id": "t", "kind": "maze", **self._maze(2)}

    def validate(self, activity: dict[str, Any], answer: Any) -> bool:
        if isinstance(answer, dict):
            return bool(answer.get("solved"))
        return bool(answer)
