"""Task 1-2: the offline gate."""
from __future__ import annotations

import math

import pytest


def results(detected, events=None, false_alarms=None, hours=None, n=20):
    events = events or [1] * n
    false_alarms = false_alarms or [0] * n
    hours = hours or [0.2] * n
    return {f"e{i}": {"n_events": events[i], "n_detected": detected[i], "n_false_alarms": false_alarms[i],
                      "normal_hours": hours[i]} for i in range(n)}


CURRENT = results([1] * 12 + [0] * 8)          # recall 0.60


def test_pooled_metrics(fg):
    u = fg["update"]
    r = results([1, 0, 1, 1], events=[1, 1, 2, 1], false_alarms=[1, 0, 0, 3], hours=[1.0, 1.0, 0.5, 0.5], n=4)
    assert u.pooled_recall(r.values()) == pytest.approx(3 / 5)
    assert u.pooled_far(r.values()) == pytest.approx(4 / 3)
    assert math.isnan(u.pooled_recall([]))


def test_clearly_worse_candidate_is_rejected(fg):
    worse = results([1] * 4 + [0] * 16)
    for policy in ("superiority", "non_inferiority"):
        g = fg["update"].offline_gate(CURRENT, worse, policy=policy, margin=0.05, n_boot=1000)
        assert g["decision"] == "reject" and not g["checks"]["non_inferior"]
        assert g["diff"]["estimate"] == pytest.approx(0.2 - 0.6)


def test_clearly_better_candidate_is_promoted(fg):
    better = results([1] * 20)
    g = fg["update"].offline_gate(CURRENT, better, policy="superiority", n_boot=1000)
    assert g["decision"] == "promote" and g["checks"]["superior"]


def test_non_inferior_but_not_better_depends_on_policy(fg):
    same = results([1] * 12 + [0] * 8)        # identical outcomes: difference exactly 0 in every resample
    u = fg["update"]
    sup = u.offline_gate(CURRENT, same, policy="superiority", margin=0.05, n_boot=500)
    non = u.offline_gate(CURRENT, same, policy="non_inferiority", margin=0.05, n_boot=500)
    assert sup["decision"] == "reject" and not sup["checks"]["superior"]
    assert non["decision"] == "promote" and non["checks"]["non_inferior"]
    assert any("superiority" in r for r in sup["reasons"])


def test_guardrail_blocks_a_noisier_candidate(fg):
    noisy = results([1] * 20, false_alarms=[1] * 20)    # 20 false alarms in 4 hours = 5 per hour
    g = fg["update"].offline_gate(CURRENT, noisy, policy="superiority", max_false_alarms_per_hour=1.0, n_boot=500)
    assert g["decision"] == "reject" and not g["checks"]["guardrail"] and g["checks"]["superior"]


def test_slice_regression_blocks_promotion(fg):
    slices = {f"e{i}": ("valve" if i < 10 else "other") for i in range(20)}
    current = results([1] * 10 + [1] * 2 + [0] * 8)               # valve 10/10, other 2/10
    cand = results([1] * 8 + [0] * 2 + [1] * 10)                 # valve 8/10, other 10/10: better overall
    u = fg["update"]
    g = u.offline_gate(current, cand, policy="non_inferiority", slices=slices, slice_margin=0.1, n_boot=2000)
    assert g["checks"]["non_inferior"] and not g["checks"]["slices"] and g["decision"] == "reject"
    g = u.offline_gate(current, cand, policy="non_inferiority", slices=slices, slice_margin=0.25, n_boot=2000)
    assert g["decision"] == "promote"


def test_gate_is_paired_and_needs_the_same_experiments(fg):
    u = fg["update"]
    with pytest.raises(ValueError):
        u.offline_gate(CURRENT, results([1] * 19, n=19), n_boot=100)
    with pytest.raises(ValueError):
        u.offline_gate(CURRENT, CURRENT, policy="vibes", n_boot=100)
    # Paired: candidate detects exactly one extra fault; unpaired resampling would give a wide interval
    # that crosses 0, the paired one cannot go below 0.
    plus_one = results([1] * 13 + [0] * 7)
    g = u.offline_gate(CURRENT, plus_one, policy="non_inferiority", margin=0.05, n_boot=2000)
    assert g["diff"]["low"] >= 0.0 and g["decision"] == "promote"
