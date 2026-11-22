"""Threshold selection uses development data only; the threshold is then frozen."""
import numpy as np
import pytest


def prf(labels, flagged):
    tp = np.sum(flagged & (labels == 1))
    p = tp / flagged.sum() if flagged.any() else 0.0
    r = tp / (labels == 1).sum() if (labels == 1).any() else 0.0
    return p, r, (0.0 if p + r == 0 else 2 * p * r / (p + r))


def make(seed, n=400, shift=1.2, prevalence=0.3):
    rng = np.random.default_rng(seed)
    y = (rng.random(n) < prevalence).astype(int)
    return np.round(rng.standard_normal(n) + shift * y, 2), y        # rounding creates ties


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_best_f1_matches_brute_force(sel, seed):
    s, y = make(seed)
    thr = sel.select_threshold(s, y, "best_f1")
    best = max(prf(y, s >= v)[2] for v in np.unique(s))
    assert prf(y, s >= thr)[2] == pytest.approx(best)
    ties = [v for v in np.unique(s) if prf(y, s >= v)[2] == pytest.approx(best)]
    assert thr == pytest.approx(max(ties)), "ties are broken toward the highest threshold"


@pytest.mark.parametrize("budget", [0.0, 0.01, 0.05, 0.2])
def test_alert_budget_is_the_lowest_threshold_within_budget(sel, budget):
    s, y = make(3)
    thr = sel.select_threshold(s, y, "alert_budget", budget=budget)
    normal = s[y == 0]
    assert np.mean(normal >= thr) <= budget + 1e-12, "more normal rows are flagged than the budget allows"
    lower = np.unique(s)[np.unique(s) < thr]
    if len(lower):
        assert np.mean(normal >= lower.max()) > budget, "a lower threshold also met the budget: recall was given away"


def test_alert_budget_that_cannot_be_met_flags_nothing(sel):
    s = np.array([5.0, 5.0, 1.0, 1.0])
    y = np.array([0, 1, 0, 1])                    # the top score is shared by a normal row
    thr = sel.select_threshold(s, y, "alert_budget", budget=0.0)
    assert not np.any(s >= thr)


def test_bad_arguments_are_errors(sel):
    s, y = make(0)
    with pytest.raises(ValueError):
        sel.select_threshold(s, y, "alert_budget")            # no budget
    with pytest.raises(ValueError):
        sel.select_threshold(s, y, "youden")
    with pytest.raises(ValueError):
        sel.select_threshold(s[:10], y[:9])


def test_evaluate_at_threshold_flags_scores_at_or_above(sel):
    s = np.array([0.1, 0.5, 0.5, 0.9])
    y = np.array([0, 0, 1, 1])
    out = sel.evaluate_at_threshold(s, y, 0.5)
    assert (out["precision"], out["recall"]) == (pytest.approx(2 / 3), pytest.approx(1.0))
    assert out["f1"] == pytest.approx(0.8)
    assert out["false_alarm_rate"] == pytest.approx(0.5)


def test_frozen_evaluation_chooses_on_dev_and_reports_test_at_that_threshold(sel):
    dev_s, dev_y = make(4)
    test_s, test_y = make(5)
    test_s = test_s + 2.0                          # the test scores are shifted: its own best threshold differs
    out = sel.frozen_threshold_evaluation(dev_s, dev_y, test_s, test_y, "best_f1")
    assert out["threshold"] == pytest.approx(sel.select_threshold(dev_s, dev_y, "best_f1"))
    p, r, f1 = prf(test_y, test_s >= out["threshold"])
    assert (out["test"]["precision"], out["test"]["recall"], out["test"]["f1"]) == (
        pytest.approx(p), pytest.approx(r), pytest.approx(f1))
    p, r, f1 = prf(dev_y, dev_s >= out["threshold"])
    assert out["dev"]["f1"] == pytest.approx(f1)
    best_on_test = max(prf(test_y, test_s >= v)[2] for v in np.unique(test_s))
    assert out["test"]["f1"] < best_on_test - 0.02, "the reported test F1 is the test-optimal one"


def test_threshold_does_not_change_when_the_test_set_changes(sel):
    dev_s, dev_y = make(6)
    thresholds = set()
    for seed in (7, 8, 9):
        test_s, test_y = make(seed, shift=3.0)
        for rule, budget in (("best_f1", None), ("alert_budget", 0.05)):
            out = sel.frozen_threshold_evaluation(dev_s, dev_y, test_s + seed, test_y, rule, budget)
            thresholds.add((rule, round(out["threshold"], 9)))
    assert len(thresholds) == 2, "the threshold moved with the test data"
