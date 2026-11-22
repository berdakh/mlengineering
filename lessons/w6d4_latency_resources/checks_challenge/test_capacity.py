"""Checks for the w6d4 capacity-planning challenge (numbers) and the memo's structure."""
from __future__ import annotations

import re

import pytest

CURVE = [  # SYNTHETIC curve with a noisy pass after the first failure
    {"rate_rps": 20, "p50_ms": 11, "p95_ms": 16, "p99_ms": 21, "error_rate": 0.0},
    {"rate_rps": 40, "p50_ms": 11, "p95_ms": 30, "p99_ms": 60, "error_rate": 0.0},
    {"rate_rps": 60, "p50_ms": 12, "p95_ms": 95, "p99_ms": 180, "error_rate": 0.0},
    {"rate_rps": 80, "p50_ms": 40, "p95_ms": 140, "p99_ms": 400, "error_rate": 0.0},
    {"rate_rps": 100, "p50_ms": 30, "p95_ms": 90, "p99_ms": 300, "error_rate": 0.0},
    {"rate_rps": 120, "p50_ms": 900, "p95_ms": 3000, "p99_ms": 5000, "error_rate": 0.2},
]


def test_littles_law(cap):
    assert cap.littles_law_concurrency(50, 200) == pytest.approx(10.0)
    assert cap.littles_law_concurrency(0, 200) == 0
    assert cap.littles_law_concurrency(450, 12.5) == pytest.approx(5.625)
    with pytest.raises(ValueError):
        cap.littles_law_concurrency(-1, 10)


@pytest.mark.parametrize("lam,s,rho,expected", [
    (450, 10, 0.7, 7),     # 4.5 busy workers / 0.7 = 6.43 -> 7
    (70, 10, 0.7, 1),      # exactly 1.0 -> 1
    (71, 10, 0.7, 2),      # just over -> 2
    (450, 10, 1.0, 5),     # 4.5 -> 5
    (1000, 12, 0.5, 24),
    (0, 10, 0.7, 1),       # always at least one
])
def test_workers_needed(cap, lam, s, rho, expected):
    assert cap.workers_needed(lam, s, rho) == expected


def test_workers_needed_rejects_bad_utilisation(cap):
    for rho in (0, -0.1, 1.2):
        with pytest.raises(ValueError):
            cap.workers_needed(100, 10, rho)
    with pytest.raises(ValueError):
        cap.workers_needed(100, 0, 0.7)


def test_max_rate_within_slo(cap):
    assert cap.max_rate_within_slo(CURVE, 100) == 60, "stop at the first violation (80/s); 100/s is noise"
    assert cap.max_rate_within_slo(CURVE, 100, percentile_key="p99_ms") == 20
    assert cap.max_rate_within_slo(CURVE, 50, percentile_key="p50_ms") == 100
    assert cap.max_rate_within_slo(CURVE, 10) == 0.0
    shuffled = list(reversed(CURVE))
    assert cap.max_rate_within_slo(shuffled, 100) == 60, "sort by rate before scanning"
    errors = [dict(r, error_rate=0.01) if r["rate_rps"] == 40 else r for r in CURVE]
    assert cap.max_rate_within_slo(errors, 100) == 20, "a rate with errors above the limit does not meet the SLO"


def test_sensitivity(cap):
    rows = cap.sensitivity(450, 10, 0.7)
    assert [r["factor"] for r in rows] == [0.5, 1.0, 1.5, 2.0]
    assert [r["workers"] for r in rows] == [4, 7, 10, 13]
    assert rows[1]["arrival_rps"] == pytest.approx(450)
    custom = cap.sensitivity(100, 20, 0.8, traffic_factors=(1.0, 3.0))
    assert [r["workers"] for r in custom] == [3, 8]


def test_measured_curve_is_used(cap, target):
    curve = cap.load_curve(target / "measured_curve.csv")
    assert len(curve) >= 3 and all("p95_ms" in r for r in curve)
    assert cap.max_rate_within_slo(curve, 100.0) > 0


def test_memo_structure(target):
    path = target / "CAPACITY.md"
    assert path.is_file(), "write CAPACITY.md"
    text = path.read_text()
    headings = [h.strip().lower() for h in re.findall(r"^##\s+(.+)$", text, flags=re.M)]
    for needed in ("assumption", "calculation", "sensitivity", "risk"):
        assert any(needed in h for h in headings), f"CAPACITY.md needs a '## ...{needed}...' section"
    assert len(text.split()) >= 250, "the memo is too short to justify a number"
    assert re.search(r"\b\d+\s*worker", text, flags=re.I), "state the number of workers you recommend"
