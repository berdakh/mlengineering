"""Small Markdown helpers shared by the w8d5 checks (unique module name across sections)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w8d5_project_explanation"
PLACEHOLDERS = re.compile(r"\bTODO\b|\bTBD\b|\[fill|<your ", re.IGNORECASE)
INTERVAL = re.compile(r"\[\s*[-+]?\d*\.?\d+\s*,\s*[-+]?\d*\.?\d+\s*\]|±")


def words(text: str) -> int:
    """Count words the way a speaker would: tokens that contain a letter or a digit."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)       # code/diagram blocks are not spoken
    return len([t for t in text.split() if re.search(r"[A-Za-z0-9]", t)])


def sections(text: str, level: str = "## ") -> dict[str, str]:
    """{heading: body} for headings of the given level, in order."""
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith(level) and not line.startswith(level + "#"):
            current = line[len(level):].strip()
            out[current] = ""
        elif current is not None:
            out[current] += line + "\n"
    return out


def find_section(secs: dict[str, str], name: str) -> str | None:
    for heading, body in secs.items():
        if heading.lower().startswith(name.lower()):
            return body
    return None


def artifact_exists(path: str) -> bool:
    candidates = [ROOT / path]
    project = os.environ.get("WB_PROJECT_DIR")
    if project:
        candidates.append(Path(project).expanduser() / path)
    return any(c.exists() for c in candidates)
