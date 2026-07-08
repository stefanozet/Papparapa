"""Auto-discovery of the games in ``catalog/``.

Adding a game means dropping a module (or package) into ``catalog/`` — nothing
is registered by hand.  Discovery imports every top-level entry of the package
(names starting with ``_`` are skipped, handy for shared helpers), collects the
concrete ``Game`` subclasses defined there and validates each one at startup,
failing fast with a clear error: required attributes present, no duplicate
keys, and a playable renderer — the game's ``kind`` must match one of the
frontend's base renderers (``frontend/js/games/<kind>.js``) unless the game
ships as a folder bundling its own ``renderer.js``.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

from ..config import FRONTEND_DIR
from . import catalog
from .base import Game

_REQUIRED_ATTRS = ("key", "name", "icon", "color", "kind")
_CATALOG_DIR = Path(catalog.__path__[0]).resolve()
_BASE_KINDS_DIR = FRONTEND_DIR / "js" / "games"


def _discover() -> list[type[Game]]:
    """Import every catalog entry and collect its concrete ``Game`` classes."""
    for info in pkgutil.iter_modules(catalog.__path__):
        if not info.name.startswith("_"):
            importlib.import_module(f"{catalog.__name__}.{info.name}")

    found: list[type[Game]] = []
    stack = list(Game.__subclasses__())
    while stack:
        cls = stack.pop()
        stack.extend(cls.__subclasses__())
        # Only classes defined inside catalog/ count: intermediate bases like
        # ChoiceGame are abstract, test doubles live in other packages.
        if not inspect.isabstract(cls) and cls.__module__.startswith(catalog.__name__):
            found.append(cls)
    return found


def _bundled_renderer(cls: type[Game]) -> Path | None:
    """The game's own ``renderer.js``, when it ships one in its folder.

    Only games packaged as a folder can bundle a renderer: a single-file game
    sits directly in ``catalog/``, where a stray ``renderer.js`` would attach
    itself to every such game.
    """
    folder = Path(inspect.getfile(cls)).resolve().parent
    if folder == _CATALOG_DIR:
        return None
    path = folder / "renderer.js"
    return path if path.is_file() else None


def _validate(cls: type[Game], renderer: Path | None) -> None:
    missing = [a for a in _REQUIRED_ATTRS if getattr(cls, a, None) is None]
    if missing:
        raise RuntimeError(
            f"Game {cls.__module__}.{cls.__name__} is missing required "
            f"attribute(s): {', '.join(missing)}"
        )
    # When the frontend is deployed elsewhere the base kinds can't be checked
    # from here; validate only against a locally present frontend/js/games/.
    if (
        renderer is None
        and _BASE_KINDS_DIR.is_dir()
        and not (_BASE_KINDS_DIR / f"{cls.kind}.js").is_file()
    ):
        raise RuntimeError(
            f"Game '{cls.key}' uses kind '{cls.kind}' but there is no base "
            f"renderer frontend/js/games/{cls.kind}.js and the game does not "
            "bundle its own renderer.js"
        )


def _build() -> dict[str, Game]:
    games: dict[str, Game] = {}
    for cls in sorted(_discover(), key=lambda c: getattr(c, "key", None) or ""):
        renderer = _bundled_renderer(cls)
        _validate(cls, renderer)
        if cls.key in games:
            raise RuntimeError(
                f"Duplicate game key '{cls.key}': "
                f"{type(games[cls.key]).__module__} and {cls.__module__}"
            )
        game = cls()
        game.renderer_path = renderer
        games[cls.key] = game
    return games


GAMES: dict[str, Game] = _build()
