"""Markdown helpers for the w8d7 checks (unique module name across sections)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("lessons/w8d7_retrospective")
PLACEHOLDERS = re.compile(r"\bTODO\b|\bTBD\b", re.IGNORECASE)


def words(text: str) -> int:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    return len([t for t in text.split() if re.search(r"[A-Za-z0-9]", t)])


def table_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or set(line) <= set("|-: "):
            continue
        rows.append([c.strip() for c in line.strip("|").split("|")])
    return rows[1:]  # drop the header


def artifact_exists(path: str) -> bool:
    candidates = [ROOT / path]
    project = os.environ.get("WB_PROJECT_DIR")
    if project:
        candidates.append(Path(project).expanduser() / path)
    return any(c.exists() for c in candidates)


def read(name: str) -> str:
    path = TARGET / name
    assert path.is_file(), f"missing {path}"
    return path.read_text()
