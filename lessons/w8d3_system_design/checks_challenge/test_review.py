"""Structural checks of the design review. They cannot judge whether a finding is right; the rubric
does that. They check that the review is complete enough to act on and covers the sections that a
design review of this doc must cover."""
from __future__ import annotations

from conftest import SEVERITIES, section_numbers


def test_at_least_six_findings(review):
    assert len(review["rows"]) >= 6, f"found {len(review['rows'])} findings; a useful review has at least 6"


def test_every_finding_cites_an_existing_section(review):
    for row in review["rows"]:
        nums = section_numbers(row["section"])
        assert nums and all(1 <= n <= 9 for n in nums), f"{row['id']}: section {row['section']!r} not in §1-§9"


def test_severities_are_from_the_scale(review):
    bad = [r["id"] for r in review["rows"] if r["severity"] not in SEVERITIES]
    assert not bad, f"severity must be one of {sorted(SEVERITIES)}: {bad}"


def test_every_fix_is_concrete(review):
    vague = [r["id"] for r in review["rows"] if len(r["fix"].split()) < 8 or r["fix"] in {"?", "TBD"}]
    assert not vague, f"fixes need at least eight words saying what to do instead: {vague}"


def test_at_least_two_blockers(review):
    assert sum(r["severity"] == "blocker" for r in review["rows"]) >= 2


def test_core_sections_reviewed(review):
    cited = {n for r in review["rows"] for n in section_numbers(r["section"])}
    # A review of this doc must address the labels (§3), features available at prediction time (§4),
    # the evaluation protocol (§5) and the serving arithmetic (§6).
    missing = {3, 4, 5, 6} - cited
    assert not missing, f"no finding on section(s) {sorted(missing)}"


def test_problems_in_features_or_evaluation_are_blockers(review):
    worst = {}
    order = {"minor": 0, "major": 1, "blocker": 2}
    for r in review["rows"]:
        for n in section_numbers(r["section"]):
            worst[n] = max(worst.get(n, -1), order.get(r["severity"], -1))
    assert worst.get(4) == 2 or worst.get(5) == 2, (
        "nothing in §4 (features) or §5 (evaluation) is rated blocker: would you build it as written?")


def test_verdict_and_summary(review):
    assert review["verdict"], "write 'Verdict: ...'"
    assert review["verdict"] not in {"approve", "approved", "<approve | approve with changes | reject and redesign>"}, (
        "a doc with blockers cannot be approved as is")
    words = len(review["summary"].split())
    assert 15 <= words <= 120, f"summary has {words} words; write 15-120"
