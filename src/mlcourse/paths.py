"""Locate the repository and the course's data files."""
from __future__ import annotations

import json
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """The first directory at or above `start` (default: cwd) that holds src/mlcourse."""
    start = (start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "src" / "mlcourse").is_dir() and (candidate / "course.json").is_file():
            return candidate
    raise FileNotFoundError("not inside the course repository (no src/mlcourse above the current directory)")


def units(root: Path | None = None) -> list[dict]:
    """Every session in course.json, in schedule order."""
    root = root or repo_root()
    return json.loads((root / "course.json").read_text())["units"]


def find_unit(token: str, root: Path | None = None) -> dict:
    """Resolve 'w1d3', 'w1d3_package_structure' or a notebook number such as '03'."""
    token = token.strip().strip("/")
    matches = [u for u in units(root)
               if token in (u["id"], u.get("notebook", ""), u.get("path") or "")
               or u["id"].startswith(token + "_")
               or (u.get("notebook") or "").startswith(token + "_")]
    if len(matches) != 1:
        raise KeyError(f"{token!r} matched {len(matches)} sessions")
    return matches[0]
