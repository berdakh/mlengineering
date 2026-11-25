"""Checks for f4. They grade the metric implementation and the *properties* a baseline must have
(valid scores, no use of test labels, reproducible, better than no-skill). They do not prescribe a
model family, a feature set or a heuristic."""
import numpy as np
import pytest
from sklearn.metrics import average_precision_score

LABEL = "lapsed_30d"


def valid_scores(scores, n):
    scores = np.asarray(scores, dtype=float)
    assert scores.shape == (n,), f"expected one score per test row ({n},), got {scores.shape}"
    assert np.isfinite(scores).all(), "scores contain NaN or inf"
    return scores


# ------------------------------------------------------- precision / recall at a call budget
def test_precision_recall_top_fraction(sub):
    y = [0, 1, 1, 0, 0, 1, 0, 0, 0, 0]
    s = [0.95, 0.9, 0.85, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.0]
    p, r = sub.precision_recall_at_fraction(y, s, 0.3)      # top 3 rows: labels 0, 1, 1
    assert p == pytest.approx(2 / 3) and r == pytest.approx(2 / 3)
    p, r = sub.precision_recall_at_fraction(y, s, 0.1)      # top 1 row
    assert p == pytest.approx(0.0) and r == pytest.approx(0.0)


def test_precision_recall_uses_rank_not_a_score_threshold(sub):
    y = [0, 1, 0, 0]
    low = [0.01, 0.04, 0.02, 0.03]       # all scores far below 0.5: the top 25% is still one row
    p, r = sub.precision_recall_at_fraction(y, low, 0.25)
    assert p == pytest.approx(1.0) and r == pytest.approx(1.0)


def test_precision_recall_rounds_k_up_and_accepts_unsorted_input(sub):
    y = np.array([1, 0, 0, 1, 0])
    s = np.array([0.7, 0.1, 0.2, 0.9, 0.3])
    p, r = sub.precision_recall_at_fraction(y, s, 0.3)      # ceil(1.5) = 2 rows flagged
    assert p == pytest.approx(1.0) and r == pytest.approx(1.0)


# ------------------------------------------------------- trivial baseline
def test_trivial_is_constant_train_rate(sub, train, test):
    scores = valid_scores(sub.trivial_scores(train, test), len(test))
    assert np.allclose(scores, train[LABEL].mean())


# ------------------------------------------------------- heuristic baseline
def test_heuristic_is_a_usable_ranking(sub, train, test):
    scores = valid_scores(sub.heuristic_scores(train, test), len(test))
    assert len(np.unique(scores)) > 1, "a heuristic must rank accounts, not score them all the same"


def test_heuristic_does_not_need_test_labels(sub, train, test):
    with_labels = valid_scores(sub.heuristic_scores(train, test), len(test))
    without = valid_scores(sub.heuristic_scores(train, test.drop(columns=[LABEL])), len(test))
    assert np.allclose(with_labels, without)


# ------------------------------------------------------- model baseline
def test_model_scores_valid(model_scores, test):
    valid_scores(model_scores, len(test))


def test_model_does_not_need_test_labels(sub, model_scores, train, test):
    """At prediction time the outcome does not exist yet. Scoring must work without it,
    and must give the same scores."""
    without = valid_scores(sub.model_scores(train, test.drop(columns=[LABEL])), len(test))
    assert np.allclose(without, model_scores, atol=1e-6), "scores change when test labels are removed"


def test_model_is_reproducible(sub, model_scores, train, test):
    again = valid_scores(sub.model_scores(train, test), len(test))
    assert np.allclose(again, model_scores, atol=1e-6), "two identical runs give different scores; fix the seed"


def test_model_beats_no_skill(model_scores, test):
    y = test[LABEL].to_numpy()
    ap = average_precision_score(y, model_scores)
    assert ap > 1.4 * y.mean(), (
        f"model average precision {ap:.3f} is not clearly above the no-skill level {y.mean():.3f}; "
        "check that you return continuous risk scores, not 0/1 predictions")


# ------------------------------------------------------- report
def test_run_report_is_consistent(sub, model_scores, train, test):
    report = sub.run()
    y = test[LABEL].to_numpy()
    assert report["test_prevalence"] == pytest.approx(y.mean())
    for name in ("trivial", "heuristic", "model"):
        assert set(report[name]) >= {"ap", "precision_at_budget", "recall_at_budget"}, name
    assert report["trivial"]["ap"] == pytest.approx(y.mean(), abs=1e-6), \
        "a constant score has average precision equal to the prevalence"
    assert report["model"]["ap"] == pytest.approx(average_precision_score(y, model_scores), abs=1e-6)
    p, r = sub.precision_recall_at_fraction(y, model_scores, 0.08)
    assert report["model"]["precision_at_budget"] == pytest.approx(p)
    assert report["model"]["recall_at_budget"] == pytest.approx(r)
