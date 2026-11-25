"""Structure of the scoping memo. The reviewer judges quality; these checks only make sure the memo can be judged."""
from __future__ import annotations

import re

import pytest

DECISIONS = {"fix now", "defer", "scope out"}


def section(memo: str, title: str) -> str:
    parts = re.split(r"^## ", memo, flags=re.M)
    for p in parts:
        if p.lower().startswith(title.lower()):
            return p.split("\n", 1)[1] if "\n" in p else ""
    raise AssertionError(f"missing section '## {title}'")


@pytest.fixture(scope="module")
def gaps(memo) -> list[dict]:
    rows = []
    for line in section(memo, "Gap list").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and cells[0].isdigit():
            rows.append(dict(zip(["n", "gap", "evidence", "impact", "effort", "decision", "reason"], cells)))
    return rows


@pytest.fixture(scope="module")
def hours(memo) -> float:
    m = re.search(r"Time available before submission:\s*([0-9]+(?:\.[0-9]+)?)\s*h", memo)
    assert m, "state the hours available in the header, e.g. 'Time available before submission: 5 h'"
    return float(m.group(1))


def test_no_placeholders(memo):
    left = re.findall(r"<[^>\n]{1,60}>|\bTODO\b", memo)
    assert not left, f"placeholders left: {left[:5]}"


def test_at_least_four_gaps(gaps):
    assert len(gaps) >= 4, f"list at least four gaps (found {len(gaps)})"


def test_rows_complete(gaps):
    for g in gaps:
        assert g["gap"] and g["evidence"] and g["impact"], f"gap {g['n']}: gap, evidence and impact are required"
        assert g["decision"].lower() in DECISIONS, f"gap {g['n']}: decision must be one of {sorted(DECISIONS)}"
        assert len(g["reason"].split()) >= 6, f"gap {g['n']}: give a reason of six or more words"
        assert re.fullmatch(r"[0-9]+(\.[0-9]+)?", g["effort"]), f"gap {g['n']}: effort must be a number of hours"


def test_something_is_deferred_or_dropped(gaps):
    assert any(g["decision"].lower() != "fix now" for g in gaps), (
        "every gap is 'fix now': with a fixed time budget that is a plan to miss the deadline, not a scope")


def test_fix_now_fits_the_time(gaps, hours):
    total = sum(float(g["effort"]) for g in gaps if g["decision"].lower() == "fix now")
    assert total <= hours, f"'fix now' efforts add up to {total} h but only {hours} h are available"


def test_scoped_out_explanation(memo):
    text = section(memo, "What I will say")
    assert len(text.split()) >= 40, "explain the scoped-out items in at least 40 words"


def test_scoping_decisions_present(memo):
    assert len(section(memo, "Scoping decisions").split()) >= 30, "write the scoping decisions (30+ words)"
