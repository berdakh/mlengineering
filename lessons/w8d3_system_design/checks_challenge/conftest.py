"""Fixtures for the w8d3 challenge checks: they parse <target>/REVIEW.md (structure only)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w8d3_system_design"
SEVERITIES = {"blocker", "major", "minor"}


def parse_review(text: str) -> dict:
    rows = []
    in_table = False
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.strip().startswith("|") else None
        if cells and [c.lower() for c in cells[:2]] == ["id", "section"]:
            in_table = True
            continue
        if in_table and cells is None:
            in_table = False
        if in_table and cells and not set("".join(cells)) <= set("-: "):
            if len(cells) >= 5:
                rows.append({"id": cells[0], "section": cells[1], "severity": cells[2].lower(),
                             "finding": cells[3], "fix": cells[4]})
    verdict = re.search(r"^Verdict:\s*(.+)$", text, flags=re.M)
    summary = text.split("## Summary", 1)[1] if "## Summary" in text else ""
    summary = "\n".join(l for l in summary.splitlines()[1:] if l.strip())
    return {"rows": rows, "verdict": verdict.group(1).strip().lower() if verdict else "", "summary": summary}


def section_numbers(cell: str) -> list[int]:
    return [int(n) for n in re.findall(r"§\s*(\d+)", cell)]


@pytest.fixture(scope="session")
def review() -> dict:
    path = resolve_target(UNIT, "challenge") / "REVIEW.md"
    assert path.is_file(), f"missing {path}"
    return parse_review(path.read_text())
