"""Checks for the w4d5 challenge (SYNTHETIC churn decision case)."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score


def test_aucs_and_difference(results, cases):
    preds = pd.read_csv(cases["default"] / "predictions.csv")
    r = results["default"]
    assert r["auc_a"] == pytest.approx(roc_auc_score(preds["churned"], preds["score_a"]), abs=1e-9)
    assert r["auc_b"] == pytest.approx(roc_auc_score(preds["churned"], preds["score_b"]), abs=1e-9)
    assert r["diff"] == pytest.approx(r["auc_b"] - r["auc_a"], abs=1e-12)
    assert r["diff_lo"] <= r["diff"] <= r["diff_hi"]


def test_interval_resamples_regions_not_customers(results, reference_widths):
    r = results["default"]
    width = r["diff_hi"] - r["diff_lo"]
    assert width > 1.2 * reference_widths["row"], (
        f"interval width {width:.4f} is about as narrow as a customer-level bootstrap "
        f"({reference_widths['row']:.4f}); customers in one region are not independent")
    assert 0.65 * reference_widths["cluster"] < width < 1.5 * reference_widths["cluster"], (
        f"interval width {width:.4f} is far from a paired region-level bootstrap ({reference_widths['cluster']:.4f})")


def test_p95_latency(results, cases):
    lat = pd.read_csv(cases["default"] / "latency_ms.csv")
    for m in ("a", "b"):
        expected = np.percentile(lat.loc[lat["model"] == m.upper(), "ms"], 95)
        assert results["default"][f"p95_ms_{m}"] == pytest.approx(expected, rel=1e-9)


def test_default_case_keeps_a(results):
    r = results["default"]
    assert r["vs_reference"] == "inconclusive"
    assert r["meets_latency_a"] and not r["meets_latency_b"]
    assert r["choice"] == "A" and r["reason"]


def test_small_gain_does_not_win_even_when_fast_enough(results):
    r = results["default_loose_latency"]
    assert r["meets_latency_b"], "case.json says 500 ms; read the budget from the case"
    assert r["choice"] == "A", "+0.01 with an interval reaching below +MPID is not a reason to switch"


def test_clear_win_switches_to_b(results):
    r = results["clear_win"]
    assert r["vs_reference"] == "better"
    assert r["choice"] == "B"


def test_latency_budget_is_a_hard_constraint(results):
    r = results["clear_win_tight_latency"]
    assert not r["meets_latency_b"]
    assert r["choice"] == "A"


def test_reproducible_with_seed(analyse, cases, results):
    again = analyse(cases["default"], n_boot=300, seed=0)
    assert again["diff_lo"] == results["default"]["diff_lo"] and again["diff_hi"] == results["default"]["diff_hi"]


SECTIONS = ["context", "options", "evidence", "decision", "risks", "what would change the decision"]


def test_memo_is_written(target):
    memo = (target / "MEMO.md").read_text()
    headings = [h.strip().lower() for h in re.findall(r"^##\s+(.+)$", memo, flags=re.M)]
    for section in SECTIONS:
        assert any(h.startswith(section) for h in headings), f"MEMO.md needs a '## {section.title()}' section"
    assert "TODO" not in memo, "MEMO.md still contains TODO placeholders"
    assert re.search(r"\|.*\|", memo), "the Evidence section needs a table"
    words = len(re.findall(r"\w+", memo))
    assert 250 <= words <= 900, f"a one-page memo is roughly 250-900 words; this one has {words}"
