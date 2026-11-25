"""Checks for the w6d6 challenge: structure, facts and blameless language of the postmortem."""
from __future__ import annotations

import re

import pytest

from conftest import section, sections

HEADINGS = ["Summary", "Impact", "Timeline", "Root cause", "Contributing factors", "What went well",
            "What went wrong", "Action items", "Lessons"]
PEOPLE = ("Mei", "Ravi", "Dana")
BLAME = [r"\bhuman error\b", r"\bshould have\b", r"\bshould've\b", r"\bcareless", r"\bblamed?\b",
         r"\b(at|his|her|their|my|your) fault\b", r"\bnegligen", r"\bstupid", r"\bincompetent"]


@pytest.mark.parametrize("heading", HEADINGS)
def test_section_is_written(text, heading):
    body = section(text, heading).strip()
    assert len(body) >= 40 and "TODO" not in body, f"'## {heading}' is empty or still TODO"


def test_impact_duration_and_business_effect(text):
    impact = section(text, "Impact")
    assert re.search(r"\b47\s*(min|minutes)\b", impact), \
        "impact lasted from 14:02 (first request served by the release) to 14:49 (rollback complete)"
    for number in ("212", "37"):
        assert number in impact, f"quantify the business effect: {number} is in the timeline"


def test_timeline_uses_real_times_including_start_and_end(text, given_times):
    timeline = section(text, "Timeline")
    times = re.findall(r"\b(\d\d:\d\d)\b", timeline)
    assert len(times) >= 8, "at least eight timeline entries"
    invented = sorted(set(times) - given_times)
    assert not invented, f"times not in the given timeline: {invented}"
    assert "14:02" in times and "14:49" in times, "include the start (14:02) and end (14:49) of impact"


def test_action_items_table(text):
    rows = [ln for ln in section(text, "Action items").splitlines() if ln.strip().startswith("|")]
    assert rows, "action items must be a Markdown table"
    header = [c.strip().lower() for c in rows[0].strip("|").split("|")]
    for col in ("action", "type", "owner", "due"):
        assert col in header, f"action-item table needs a '{col}' column"
    body = [[c.strip() for c in r.strip("|").split("|")] for r in rows[2:]]
    body = [r for r in body if any(r)]
    assert len(body) >= 4, "at least four action items"
    types = [r[header.index("type")].lower() for r in body]
    assert all(t in {"prevent", "detect", "mitigate", "process"} for t in types), f"bad types: {types}"
    assert "detect" in types and "prevent" in types, "at least one detect and one prevent item"
    for r in body:
        assert r[header.index("owner")] and r[header.index("due")], f"every action needs an owner and a due date: {r}"


def test_blameless_language(text):
    low = text.lower()
    found = [w for w in BLAME if re.search(w, low)]
    assert not found, f"blameless format: avoid {found}"
    for name in ("Root cause", "Contributing factors"):
        body = section(text, name)
        named = [p for p in PEOPLE if re.search(rf"\b{p}\b", body)]
        assert not named, f"'{name}' names {named}: describe the system and conditions, not people"
