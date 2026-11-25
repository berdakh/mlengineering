"""Structure checks for the milestone-1 submission. They cannot judge quality; the reviewer does."""
from __future__ import annotations

import re

CRITERIA = ["one-command rebuild", "reproducibility", "evaluation protocol", "results and uncertainty",
            "error analysis", "decision and limitations", "code and repository hygiene"]


def field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", text, flags=re.M)
    return m.group(1).strip() if m else ""


def test_no_placeholders_left(submission):
    assert "TODO" not in submission, "replace every TODO"


def test_header_fields(submission):
    assert re.fullmatch(r"`?[0-9a-f]{7,40}(-dirty)?`?", field(submission, "Commit")), \
        "Commit: give the hash of the commit that produced the report"
    assert not field(submission, "Commit").strip("`").endswith("-dirty"), \
        "the report must come from a committed state, not a dirty working tree"
    assert re.search(r"https?://|git@", field(submission, "Repository")), "Repository: give a URL"
    assert field(submission, "Command"), "Command: give the exact rebuild command"
    assert field(submission, "Report").endswith(".md"), "Report: give the path of the generated markdown report"


def test_checklist_complete(submission):
    items = re.findall(r"^- \[(.*?)\]\s*(.*)$", submission, flags=re.M)
    assert len(items) >= 12, "keep every checklist item"
    for mark, text in items:
        assert mark in ("x", "X", "n/a"), f"unticked checklist item: {text[:70]}"
        if mark == "n/a":
            assert re.search(r"(n/a|N/A).*?[:-]\s*\S+", f"{mark} {text}") or len(text.split()) >= 12, \
                f"an n/a item needs a reason: {text[:70]}"


def test_self_review_scored_with_evidence(submission):
    rows = {}
    for line in submission.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0].lower() in CRITERIA:
            rows[cells[0].lower()] = cells
    missing = [c for c in CRITERIA if c not in rows]
    assert not missing, f"self-review rows missing: {missing}"
    for name, (_, score, evidence) in rows.items():
        assert score in {"1", "2", "3"}, f"{name}: score must be 1, 2 or 3"
        assert len(evidence.split()) >= 8, f"{name}: evidence needs at least one concrete sentence"


def test_questions_for_reviewer(submission):
    part = submission.split("## Questions for the reviewer", 1)
    assert len(part) == 2, "keep the 'Questions for the reviewer' section"
    questions = [ln for ln in part[1].splitlines()
                 if ln.strip().startswith("- ") and len(ln.split()) >= 6 and "TODO" not in ln]
    assert questions, "ask at least one specific question"
