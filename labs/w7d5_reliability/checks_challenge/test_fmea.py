"""Challenge part 1: the failure-mode table in FMEA.md. Structure only; the reviewer judges the content."""
from __future__ import annotations

import re

import pytest

HEADER = ["failure", "category", "detection", "impact", "mitigation", "test"]
CATEGORIES = {"input", "model", "artifact", "dependency", "resource", "stream", "deployment"}
MUST_COVER = [{"input"}, {"model", "artifact"}, {"dependency"}, {"resource"}, {"stream"}]


@pytest.fixture(scope="module")
def rows(target):
    text = (target / "FMEA.md").read_text()
    table, header = [], None
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        table.append(dict(zip(header, cells)))
    assert header == HEADER, f"the header row must be | {' | '.join(h.title() for h in HEADER)} |, got {header}"
    return table


def test_enough_rows_and_no_placeholders(rows, target):
    assert len(rows) >= 10, f"at least 10 failure modes, found {len(rows)}"
    assert "TODO" not in (target / "FMEA.md").read_text(), "replace every TODO"


def test_every_cell_says_something(rows):
    for r in rows:
        for col in ("failure", "detection", "impact", "mitigation"):
            assert len(r.get(col, "").split()) >= 3, f"row '{r.get('failure', '')[:40]}': '{col}' needs a real entry"
        assert re.search(r"test|drill", r.get("test", ""), flags=re.I), \
            f"row '{r.get('failure', '')[:40]}': 'test' must name the test or drill that produces this failure"


def test_categories_valid_and_covered(rows):
    cats = [r["category"].lower() for r in rows]
    bad = [c for c in cats if c not in CATEGORIES]
    assert not bad, f"unknown categories {bad}; use {sorted(CATEGORIES)}"
    for need in MUST_COVER:
        assert need & set(cats), f"no failure mode in category {' or '.join(sorted(need))}"


def test_the_two_mitigations_are_in_the_table(rows):
    text = " ".join(r["mitigation"] + " " + r["test"] for r in rows).lower()
    assert re.search(r"circuit ?breaker", text), "one row should be mitigated by your CircuitBreaker"
    assert re.search(r"sampleorderguard|order(ing)? guard", text), "one row should be mitigated by your SampleOrderGuard"
