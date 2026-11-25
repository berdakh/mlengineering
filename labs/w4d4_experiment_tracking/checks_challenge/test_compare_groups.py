"""Checks for challenge/compare_groups.py (SYNTHETIC index; behaviour only)."""
from __future__ import annotations

import math

import pytest

A = {"detector.n_estimators": 200}
B = {"detector.n_estimators": 50}


def test_pairs_only_seeds_present_in_both_groups(cg, index, expected):
    out = cg.compare_groups(index, A, B, "ap")
    assert out["n_pairs"] == 4
    assert [p["seed"] for p in out["pairs"]] == [0, 1, 2, 3]
    assert out["unmatched_a"] == [4] and out["unmatched_b"] == [7]


def test_mean_of_paired_differences_not_difference_of_means(cg, index, expected):
    out = cg.compare_groups(index, A, B, "ap")
    assert out["mean_diff"] == pytest.approx(expected.mean()), (
        "the mean over PAIRED differences; unpaired seeds 4 and 7 must not move it")
    assert out["sd_diff"] == pytest.approx(expected.std(ddof=1))


def test_sign_is_a_minus_b(cg, index):
    out = cg.compare_groups(index, A, B, "ap")
    assert out["mean_diff"] > 0 and out["a_better"] == 4
    assert all(p["diff"] == pytest.approx(p["a"] - p["b"]) for p in out["pairs"])
    assert cg.compare_groups(index, B, A, "ap")["mean_diff"] < 0


def test_unfinished_runs_are_not_compared(cg, index):
    out = cg.compare_groups(index, A, B, "ap")
    assert 5 not in [p["seed"] for p in out["pairs"]], "seed 5 runs are partial: they carry no evidence"


def test_single_pair_has_undefined_spread(cg, index):
    small = index[index["seed"].isin([0]) | (index["status"] != "complete")]
    out = cg.compare_groups(small, A, B, "ap")
    assert out["n_pairs"] == 1 and math.isnan(out["sd_diff"])


def test_ambiguous_filter_is_an_error(cg, index):
    with pytest.raises(ValueError):
        cg.compare_groups(index, {"sweep": "iforest"}, B, "ap")


def test_no_pairs_is_an_error(cg, index):
    only_seven = index[index["seed"] != 7]
    with pytest.raises(ValueError):
        cg.compare_groups(only_seven[only_seven["seed"] >= 4], A, B, "ap")


def test_report_mentions_every_pair_and_the_unpaired_runs(cg, index):
    text = cg.format_report(cg.compare_groups(index, A, B, "ap"), A, B)
    assert sum(1 for line in text.splitlines() if line.startswith("| ") and not line.startswith("| pair")) == 4
    assert "7" in text and "4" in text
