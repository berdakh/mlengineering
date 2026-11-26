"""Locate the repository and the course's data files."""
from __future__ import annotations

import json
from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """The first directory at or above `start` (default: cwd) that holds src/mlcourse."""
    start = (start or Path.cwd()).resolve()
    for candidate in [start, *start.parents]:
        if (candidate / "src" / "mlcourse").is_dir() :
            return candidate
    raise FileNotFoundError("not inside the course repository (no src/mlcourse above the current directory)")


def units(root: Path | None = None) -> list[dict]:
    """Every advanced-track session (advanced/course.json), in schedule order."""
    root = root or repo_root()
    return json.loads((root / "advanced" / "course.json").read_text())["units"]


def course_notebooks(root: Path | None = None) -> list[dict]:
    """The 12-week course's notebooks (curriculum.json), each with an "id" equal to its notebook name."""
    root = root or repo_root()
    path = root / "curriculum.json"
    if not path.is_file():
        return []
    return [{**n, "id": n["notebook"], "path": None} for n in json.loads(path.read_text())["notebooks"]]


def find_unit(token: str, root: Path | None = None) -> dict:
    """Resolve 'w1d3', 'w1d3_package_structure' or a notebook number such as '03'."""
    token = token.strip().strip("/")
    course = [n for n in course_notebooks(root) if n["id"] == token or n["id"].startswith(token + "_")]
    if len(course) == 1:
        return course[0]
    matches = [u for u in units(root)
               if token in (u["id"], u.get("notebook", ""), u.get("path") or "")
               or u["id"].startswith(token + "_")
               or (u.get("notebook") or "").startswith(token + "_")]
    if len(matches) != 1:
        raise KeyError(f"{token!r} matched {len(matches)} sessions")
    return matches[0]
