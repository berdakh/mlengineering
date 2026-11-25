"""Completeness only; the rubric in assessment.md judges the content."""
from __future__ import annotations

import re

REQUIRED = ["Decision supported", "Unit of prediction", "Prediction time and horizon", "Label definition",
            "Cost of errors", "Constraints", "Success metrics", "Baseline", "Splits", "Out of scope"]


def test_framing_has_every_section_filled_in(target):
    path = target / "FRAMING.md"
    assert path.is_file(), "write your framing in challenge/FRAMING.md"
    parts = re.split(r"^##\s+(.+?)\s*$", path.read_text(), flags=re.M)
    sections = {parts[i].strip().lower(): parts[i + 1] for i in range(1, len(parts) - 1, 2)}
    for name in REQUIRED:
        body = next((b for t, b in sections.items() if t.startswith(name.lower())), None)
        assert body is not None, f"missing section: '## {name}'"
        assert "TODO" not in body, f"section '{name}' still contains TODO"
        assert len(body.split()) >= 15, f"section '{name}' is under 15 words"
