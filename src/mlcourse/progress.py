"""Record progress from a notebook. Same file and format as `python wb.py mark`.

    from mlcourse.progress import mark, status
    mark("w1d3", "reading")
    mark("w1d3", "guided")
    status()
"""
from __future__ import annotations

import datetime as dt
import json

from mlcourse.paths import find_unit, repo_root, units

FLAGS = ("reading", "guided", "independent", "review")


def _path():
    return repo_root() / "progress" / "progress.json"


def load() -> dict:
    p = _path()
    return json.loads(p.read_text()) if p.is_file() else {"units": {}}


def mark(session: str, flag: str, value: bool = True) -> None:
    """Set one of the four flags: reading, guided, independent, review."""
    if flag not in FLAGS:
        raise ValueError(f"flag must be one of {FLAGS}")
    unit = find_unit(session)
    progress = load()
    entry = progress.setdefault("units", {}).setdefault(unit["id"], {})
    entry[flag] = bool(value)
    entry["updated"] = dt.date.today().isoformat()
    p = _path()
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(progress, indent=2, sort_keys=True) + "\n")
    print(f"{unit['id']}: {flag} = {bool(value)}")


def note(session: str, text: str) -> None:
    """Append a dated note to progress/notes.md (same format as `wb.py note`)."""
    unit = find_unit(session)
    with (repo_root() / "progress" / "notes.md").open("a") as fh:
        fh.write(f"\n## {dt.date.today().isoformat()} - {unit['id']}\n\n{text.strip()}\n")
    print("note saved")


def status() -> None:
    done = load().get("units", {})
    for u in units():
        p = done.get(u["id"], {})
        flags = " ".join(f if p.get(f) else "." * len(f) for f in FLAGS)
        print(f"{u['id']:<34} {flags}")
