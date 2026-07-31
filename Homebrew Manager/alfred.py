"""Minimal, dependency-free helpers for Alfred workflow scripts."""

from __future__ import annotations

import json
import os
import sys
from typing import Any


DEBUG = os.environ.get("alfred_debug") == "1"


def log(*parts: Any) -> None:
    """Write to stderr, which Alfred's debug panel displays.

    Never log to stdout -- a Script Filter's stdout must be exactly one JSON object.
    """
    if DEBUG:
        print(*parts, file=sys.stderr)


def env(name: str, default: str = "") -> str:
    """Read a workflow / configuration variable. Everything Alfred sets is a string."""
    return os.environ.get(name, default)


def flag(name: str, default: bool = False) -> bool:
    """Read a checkbox configuration field, which Alfred gives as "0" or "1"."""
    raw = os.environ.get(name)
    return default if raw is None else raw == "1"


def cache_dir() -> str:
    """Regenerable data. Only populated when the workflow has a bundle id."""
    path = os.environ.get("alfred_workflow_cache") or "/tmp"
    os.makedirs(path, exist_ok=True)
    return path


def data_dir() -> str:
    """Persistent data the user would miss if it vanished."""
    path = os.environ.get("alfred_workflow_data") or "."
    os.makedirs(path, exist_ok=True)
    return path


class Items(list):
    """Accumulates Script Filter result rows and emits the JSON envelope."""

    def add(self, title: str, subtitle: str = "", arg: Any = None, **extra: Any) -> dict:
        item: dict[str, Any] = {"title": title}
        if subtitle:
            item["subtitle"] = subtitle
        if arg is not None:
            item["arg"] = arg
        item.update(extra)
        self.append(item)
        return item

    def emit(self, variables: dict | None = None, rerun: float | None = None,
             cache_seconds: int | None = None, loose_reload: bool = False,
             skip_knowledge: bool = False) -> None:
        payload: dict[str, Any] = {"items": list(self)}
        if variables:
            payload["variables"] = {k: str(v) for k, v in variables.items()}
        if rerun is not None:
            payload["rerun"] = rerun
        if cache_seconds is not None:
            # Alfred accepts 5..86400 seconds; only useful with "Alfred filters results".
            cache: dict[str, Any] = {"seconds": max(5, min(86400, int(cache_seconds)))}
            if loose_reload:
                cache["loosereload"] = True
            payload["cache"] = cache
        if skip_knowledge:
            payload["skipknowledge"] = True
        sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def pass_along(arg: str, variables: dict | None = None) -> None:
    """Output from a Run Script action, carrying workflow variables downstream."""
    body: dict[str, Any] = {"arg": arg}
    if variables:
        body["variables"] = {k: str(v) for k, v in variables.items()}
    sys.stdout.write(json.dumps({"alfredworkflow": body}, ensure_ascii=False))
