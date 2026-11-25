"""Completeness only. Whether the problem statement is GOOD is judged with the rubric in assessment.md."""
from __future__ import annotations

import re

REQUIRED = ["Decision supported", "Unit of prediction", "Prediction time and horizon", "Label definition",
            "Cost of errors", "Constraints", "Success metrics", "Baseline", "Splits", "Out of scope"]


def _sections(text: str) -> dict[str, str]:
    parts = re.split(r"^##\s+(.+?)\s*$", text, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}


def test_problem_statement_has_every_section_filled_in(target):
    path = target / "PROBLEM_STATEMENT.md"
    assert path.is_file(), "write your problem statement in lab/PROBLEM_STATEMENT.md"
    sections = _sections(path.read_text())
    for name in REQUIRED:
        match = [body for title, body in sections.items() if title.lower().startswith(name.lower())]
        assert match, f"missing section: '## {name}'"
        body = re.sub(r"<!--.*?-->", "", match[0], flags=re.S)
        assert "TODO" not in body, f"section '{name}' still contains TODO"
        assert len(body.split()) >= 15, f"section '{name}' is too short to be a decision (under 15 words)"
