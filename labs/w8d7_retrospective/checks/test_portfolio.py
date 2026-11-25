"""w8d7 checks: the portfolio links only to evidence that exists, covers every target capability,
and states conditions; the plan and the CV bullets have the required shape. They cannot judge
whether the evidence is good - the review and the ledger do that."""
import re

import pytest

from w8d7_text import PLACEHOLDERS, artifact_exists, read, table_rows, words

CONDITIONS = {"independent", "timed", "guided", "reviewed", "self-reported", "not demonstrated"}


@pytest.fixture(scope="module")
def portfolio():
    text = read("PORTFOLIO.md")
    assert not PLACEHOLDERS.search(text), "PORTFOLIO.md still contains a placeholder"
    rows = table_rows(text)
    assert rows, "no rows in the portfolio table"
    return rows


def test_every_capability_appears(portfolio):
    covered = set()
    for row in portfolio:
        covered |= {int(n) for n in re.findall(r"\b(10|[1-9])\b", row[0])}
    missing = sorted(set(range(1, 11)) - covered)
    assert not missing, f"capabilities with no row (write 'none' / 'not demonstrated' if so): {missing}"


def test_every_artifact_exists_or_is_declared_missing(portfolio):
    dead = []
    for row in portfolio:
        assert len(row) >= 4, f"row has {len(row)} columns; expected 4: {row}"
        paths = re.findall(r"`([^`]+)`", row[1])
        if row[1].strip().lower() == "none":
            assert "not demonstrated" in row[2].lower(), f"artifact 'none' must have conditions 'not demonstrated': {row}"
            continue
        assert paths, f"artifact must be a path in backticks or 'none': {row[1]!r}"
        dead += [p for p in paths if not artifact_exists(p)]
    assert not dead, f"artifacts not found: {dead}"


def test_every_row_states_conditions(portfolio):
    for row in portfolio:
        cond = row[2].lower()
        assert any(c in cond for c in CONDITIONS), f"conditions must use the vocabulary {sorted(CONDITIONS)}: {row[2]!r}"
        assert row[3], f"say in one line what the artifact demonstrates: {row}"


def test_next_plan_shape():
    text = read("NEXT_PLAN.md")
    assert not PLACEHOLDERS.search(text), "NEXT_PLAN.md still contains a placeholder"
    options = re.findall(r"^## Option", text, flags=re.M)
    assert len(options) >= 2, "consider at least two options"
    criteria = text.split("## Criteria")[1].split("## Plan")[0] if "## Criteria" in text and "## Plan" in text else ""
    assert words(criteria) >= 30, "state the criteria you chose by (at least 30 words)"
    weeks = re.findall(r"^\s*-\s*Week\s+(\d+)\s*:.+->.+$", text, flags=re.M)
    assert sorted(int(w) for w in weeks) == list(range(1, 9)), "eight lines '- Week N: objective -> deliverable'"


def test_project_summary_length():
    text = read("PROJECT_SUMMARY.md")
    assert not PLACEHOLDERS.search(text)
    body = re.sub(r"^#.*$", "", text, flags=re.M)
    assert 150 <= words(body) <= 400, f"{words(body)} words; one page is 150-400"


def test_cv_bullets_are_grounded():
    text = read("CV_BULLETS.md")
    assert not PLACEHOLDERS.search(text), "CV_BULLETS.md still contains a placeholder"
    bullets = [line.strip()[2:] for line in text.splitlines() if line.strip().startswith(("- ", "* "))]
    assert 3 <= len(bullets) <= 6, f"{len(bullets)} bullets; 3-6"
    for b in bullets:
        assert words(b) <= 35, f"bullet over 35 words: {b[:60]}..."
        paths = re.findall(r"`([^`]+)`", b)
        assert paths and all(artifact_exists(p) for p in paths), f"bullet without an existing artifact: {b[:60]}..."
        assert re.search(r"\d", b), f"a bullet should carry a concrete, checkable outcome (a number): {b[:60]}..."
        assert not re.search(r"\b(expert|state-of-the-art|world-class|cutting-edge)\b", b, re.I), \
            f"an adjective the artifact cannot back: {b[:60]}..."
