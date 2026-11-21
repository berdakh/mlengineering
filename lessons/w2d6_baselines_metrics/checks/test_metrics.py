"""flowguard.metrics: agreement with scikit-learn, conventions, edge cases."""
import math

import numpy as np
import pytest
from sklearn.metrics import average_precision_score, precision_score, recall_score


def _f1(p, r):
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def _cases(n_cases=60, seed=0):
    rng = np.random.default_rng(seed)
    for _ in range(n_cases):
        n = int(rng.integers(8, 300))
        y = (rng.random(n) < rng.uniform(0.05, 0.6)).astype(int)
        if y.sum() == 0:
            y[0] = 1
        scores = rng.normal(size=n) + y * rng.uniform(0, 2)
        yield y, np.round(scores, int(rng.integers(0, 4)))      # rounding creates tied scores


def test_pr_auc_matches_average_precision_including_ties(metrics):
    for y, s in _cases():
        assert metrics.pr_auc(y, s) == pytest.approx(average_precision_score(y, s), abs=1e-9)


def test_pr_auc_reference_points(metrics):
    y = np.array([0, 0, 1, 1, 0, 1])
    assert metrics.pr_auc(y, y.astype(float)) == pytest.approx(1.0)
    assert metrics.pr_auc(y, np.zeros(6)) == pytest.approx(0.5), "a constant score earns exactly the prevalence"
    assert metrics.pr_auc(np.ones(4, dtype=int), np.arange(4.0)) == pytest.approx(1.0)


def test_pr_auc_depends_only_on_the_ranking(metrics):
    for y, s in _cases(10, seed=1):
        assert metrics.pr_auc(y, np.exp(s / 3.0)) == pytest.approx(metrics.pr_auc(y, s), abs=1e-9)


def test_pr_auc_without_positives_is_nan(metrics):
    assert math.isnan(metrics.pr_auc(np.zeros(5, dtype=int), np.arange(5.0)))


def test_precision_recall_use_greater_or_equal(metrics):
    y = np.array([1, 0, 1, 1, 0])
    s = np.array([0.9, 0.8, 0.5, 0.2, 0.1])
    assert metrics.precision_recall_at_threshold(y, s, 0.5) == pytest.approx((2 / 3, 2 / 3))
    assert metrics.precision_recall_at_threshold(y, s, 0.51) == pytest.approx((1 / 2, 1 / 3))


def test_precision_recall_match_sklearn(metrics):
    for y, s in _cases(20, seed=2):
        threshold = float(np.median(s))
        flagged = (s >= threshold).astype(int)
        p, r = metrics.precision_recall_at_threshold(y, s, threshold)
        assert p == pytest.approx(precision_score(y, flagged, zero_division=0))
        assert r == pytest.approx(recall_score(y, flagged, zero_division=0))


def test_precision_recall_edge_cases(metrics):
    y = np.array([1, 0, 1])
    s = np.array([0.3, 0.2, 0.1])
    assert metrics.precision_recall_at_threshold(y, s, 10.0) == pytest.approx((0.0, 0.0)), "nothing flagged"
    p, r = metrics.precision_recall_at_threshold(np.zeros(3, dtype=int), s, 0.0)
    assert (p, r) == pytest.approx((0.0, 0.0)), "no positives at all"


def test_best_f1_threshold_is_optimal_and_consistent(metrics):
    for y, s in _cases(40, seed=3):
        threshold, f1 = metrics.best_f1_threshold(y, s)
        p, r = metrics.precision_recall_at_threshold(y, s, threshold)
        assert f1 == pytest.approx(_f1(p, r)), "returned F1 must be the F1 obtained at the returned threshold"
        brute = max(_f1(precision_score(y, s >= t, zero_division=0), recall_score(y, s >= t)) for t in np.unique(s))
        assert f1 == pytest.approx(brute), "a better threshold exists among the observed scores"


def test_length_mismatch_is_an_error(metrics):
    with pytest.raises(ValueError):
        metrics.pr_auc([0, 1, 1], [0.1, 0.2])
