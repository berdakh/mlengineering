"""Checks for challenge/seedcompare.py (behaviour only; the numbers are SYNTHETIC)."""
from __future__ import annotations

import math
import statistics

import pytest


def test_summary_matches_sample_statistics(sc):
    values = {0: 0.70, 1: 0.74, 2: 0.66, 3: 0.71, 4: 0.69}
    s = sc.seed_summary(values)
    assert s["n"] == 5
    assert s["mean"] == pytest.approx(statistics.mean(values.values()))
    assert s["sd"] == pytest.approx(statistics.stdev(values.values())), "use the sample sd (ddof = 1)"
    assert (s["min"], s["max"]) == (pytest.approx(0.66), pytest.approx(0.74))


def test_deterministic_detector_has_zero_spread(sc):
    s = sc.seed_summary({0: 0.8, 1: 0.8, 2: 0.8})
    assert s["sd"] == pytest.approx(0.0, abs=1e-12) and s["mean"] == pytest.approx(0.8)


def test_one_seed_is_refused(sc):
    with pytest.raises(ValueError):
        sc.seed_summary({0: 0.71})


def test_failed_run_is_refused_not_averaged(sc):
    with pytest.raises(ValueError):
        sc.seed_summary({0: 0.7, 1: float("nan"), 2: 0.72})


def test_clear_difference_gets_a_verdict(sc):
    a = {s: 0.85 + d for s, d in enumerate((0.01, -0.01, 0.0, 0.005, -0.005))}
    b = {s: 0.70 + d for s, d in enumerate((0.01, -0.01, 0.0, 0.005, -0.005))}
    out = sc.compare(a, b, test_halfwidth=0.05)
    assert out["verdict"] == "A better"
    assert out["difference"] == pytest.approx(0.15)
    assert sc.compare(b, a, test_halfwidth=0.05)["verdict"] == "B better"


def test_deterministic_detectors_still_need_the_test_interval(sc):
    """Two deterministic detectors: no seed spread at all, but the test set is still a sample."""
    out = sc.compare({0: 0.80, 1: 0.80}, {0: 0.78, 1: 0.78}, test_halfwidth=0.10)
    assert out["verdict"] == "cannot tell", "a 0.02 gap inside a +-0.10 test interval is not a result"


def test_seed_spread_can_swamp_a_difference(sc):
    """Noisy seeds: the means differ by more than the test half-width but less than the seed noise."""
    a = {0: 0.60, 1: 0.90, 2: 0.65, 3: 0.88, 4: 0.72}
    b = {0: 0.70, 1: 0.71, 2: 0.69, 3: 0.70, 4: 0.70}
    out = sc.compare(a, b, test_halfwidth=0.01)
    assert out["difference"] == pytest.approx(0.05)
    assert out["verdict"] == "cannot tell", "the seed spread of A is larger than the gap"
    expected_se = math.sqrt(statistics.stdev(a.values()) ** 2 / 5 + statistics.stdev(b.values()) ** 2 / 5)
    assert out["seed_se"] == pytest.approx(expected_se)


def test_negative_halfwidth_is_rejected(sc):
    with pytest.raises(ValueError):
        sc.compare({0: 0.7, 1: 0.7}, {0: 0.6, 1: 0.6}, test_halfwidth=-0.1)


def test_table_lists_every_detector(sc):
    text = sc.format_table({"AE": {0: 0.7, 1: 0.72}, "Mahalanobis": {0: 0.8, 1: 0.8}})
    lines = [line for line in text.splitlines() if line.startswith("|")]
    assert len(lines) == 4, "header, separator and one row per detector"
    assert "AE" in text and "Mahalanobis" in text
