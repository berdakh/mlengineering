"""Structure checks for the milestone-4 submission. They cannot judge quality; the reviewer does."""
from __future__ import annotations

import re

CRITERIA = ["reproducible demo", "coverage of failure scenarios", "report integrity",
            "service lifecycle and rollback", "runbook usefulness", "honesty about limitations"]


def field(text: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+)$", text, flags=re.M)
    return m.group(1).strip() if m else ""


def test_no_placeholders_left(submission):
    assert "TODO" not in submission, "replace every TODO"


def test_header_fields(submission):
    assert re.search(r"https?://|git@", field(submission, "Repository")), "Repository: give a URL"
    assert re.fullmatch(r"`?[0-9a-f]{7,40}`?", field(submission, "Commit")), "Commit: give a commit hash"
    assert re.fullmatch(r"`?v\d+\.\d+\.\d+(-[0-9A-Za-z.]+)?`?", field(submission, "Tag")), "Tag: e.g. v0.9.0-m4"
    for name in ("Demo command", "Report", "Runbook"):
        assert field(submission, name), f"{name}: fill it in"


def test_demo_results_are_numbers(submission):
    for name in ("Events", "Events as expected", "Faults labelled", "Faults detected"):
        assert re.fullmatch(r"\d+", field(submission, name)), f"{name}: an integer from results.json"
    assert re.fullmatch(r"\d+(\.\d+)?", field(submission, "Drift threshold")), "Drift threshold: a number"
    assert int(field(submission, "Events as expected")) <= int(field(submission, "Events"))
    not_expected = field(submission, "Not as expected")
    assert not_expected, "Not as expected: list the events or write 'none'"
    if int(field(submission, "Events as expected")) < int(field(submission, "Events")):
        assert not_expected.lower() != "none", "some events were not as expected: name them"


def test_checklist_complete(submission):
    items = re.findall(r"^- \[(.*?)\]\s*(.*)$", submission, flags=re.M)
    assert len(items) >= 12, "keep every checklist item"
    for mark, text in items:
        assert mark in ("x", "X", "n/a"), f"unticked checklist item: {text[:70]}"
        if mark == "n/a":
            assert len(text.split()) >= 12, f"an n/a item needs a reason: {text[:70]}"


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
