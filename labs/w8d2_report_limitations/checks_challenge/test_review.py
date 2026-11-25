"""Structure of the review and coverage of the planted problems (by line number)."""
from __future__ import annotations

import re

import pytest

# Text that identifies the line of each planted problem in FLAWED_REPORT.md. The explanations are in the
# solutions folder; the checks only need the locations.
PLANTED = [
    "days_since_last_reminder, and month",
    "split the 48,000 invoices at random",
    "maximised F1 on the test set",
    "94.1 % accuracy",
    "significantly better than the logistic",
    "finds 0.62 of the late",
    "Reducing invoice amounts will cause",
    "German market",
    "None identified",
]


@pytest.fixture(scope="module")
def issues(review) -> list[dict]:
    rows = []
    for line in review.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0].isdigit():
            rows.append(dict(zip(["n", "line", "problem", "why", "change", "severity"], cells)))
    return rows


def test_no_placeholders(review):
    left = re.findall(r"<[^>\n]{1,60}>|\bTODO\b", review)
    assert not left, f"placeholders left: {left[:5]}"


def test_enough_issues(issues):
    assert len(issues) >= 6, f"list at least six issues (found {len(issues)})"


def test_rows_complete(issues):
    for i in issues:
        assert re.fullmatch(r"\d+", i["line"]), f"issue {i['n']}: give the line number in FLAWED_REPORT.md"
        assert i["problem"] and i["why"], f"issue {i['n']}: problem and why-it-matters are required"
        assert len(i["change"].split()) >= 6, f"issue {i['n']}: request a concrete change (6+ words)"
        assert i["severity"].lower() in {"major", "minor"}, f"issue {i['n']}: severity must be major or minor"


def test_majors(issues):
    assert sum(i["severity"].lower() == "major" for i in issues) >= 3, "at least three issues should be major"


def test_coverage_of_planted_problems(issues, flawed_lines):
    reviewed = {int(i["line"]) for i in issues if i["line"].isdigit()}
    found = []
    for phrase in PLANTED:
        where = [n for n, text in enumerate(flawed_lines, 1) if phrase in text]
        assert where, f"check data out of date: {phrase!r} not in FLAWED_REPORT.md"
        if where[0] in reviewed:
            found.append(phrase)
    assert len(found) >= 5, f"your issues point at {len(found)} of the planted problems; find at least five"


def test_summary_and_recommendation(review):
    for title, words in (("Summary for the author", 30), ("Recommendation", 15)):
        m = re.search(rf"^## {title}\s*\n(.*?)(?=^## |\Z)", review, flags=re.M | re.S)
        assert m and len(m.group(1).split()) >= words, f"write the '{title}' section ({words}+ words)"
