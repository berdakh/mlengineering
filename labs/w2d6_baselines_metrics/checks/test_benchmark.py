"""flowguard.benchmark.evaluate_scores: threshold from dev only, report on test. SYNTHETIC data."""
import numpy as np
import pytest
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

import synth


@pytest.fixture()
def case():
    return synth.benchmark_tidy(seed=0)


def _masks(tidy, manifest, burn_in=0):
    dev = [e for fold in manifest["dev_folds"] for e in fold]
    usable = (tidy["t"] >= burn_in).to_numpy()
    return (tidy["experiment_id"].isin(dev).to_numpy() & usable,
            tidy["experiment_id"].isin(manifest["test"]).to_numpy() & usable)


def test_result_structure(benchmark, case):
    tidy, scores, manifest = case
    result = benchmark.evaluate_scores(tidy, scores, manifest)
    assert {"threshold", "dev", "test", "test_by_family"} <= set(result)
    for part in (result["dev"], result["test"], *result["test_by_family"].values()):
        assert {"pr_auc", "precision", "recall", "f1"} <= set(part)
    assert set(result["test_by_family"]) == {"other", "valve1"}


def test_threshold_is_the_best_f1_threshold_on_dev(benchmark, case):
    tidy, scores, manifest = case
    is_dev, _ = _masks(tidy, manifest)
    y, s = tidy["anomaly"].to_numpy()[is_dev], scores[is_dev]
    threshold = benchmark.evaluate_scores(tidy, scores, manifest)["threshold"]
    best = max(f1_score(y, s >= t) for t in np.unique(s))
    assert f1_score(y, s >= threshold) == pytest.approx(best)


def test_threshold_never_sees_test_rows(benchmark, case):
    """Change everything about the test experiments: the threshold must not move."""
    tidy, scores, manifest = case
    _, is_test = _masks(tidy, manifest)
    before = benchmark.evaluate_scores(tidy, scores, manifest)["threshold"]
    altered_scores = scores.copy()
    altered_scores[is_test] = altered_scores[is_test] * 3.0 + 10.0
    altered = tidy.copy()
    altered.loc[is_test, "anomaly"] = 1 - altered.loc[is_test, "anomaly"]
    after = benchmark.evaluate_scores(altered, altered_scores, manifest)["threshold"]
    assert after == pytest.approx(before), "the decision threshold changed when only TEST data changed"


def test_test_metrics_are_computed_at_the_frozen_threshold(benchmark, case):
    tidy, scores, manifest = case
    _, is_test = _masks(tidy, manifest)
    result = benchmark.evaluate_scores(tidy, scores, manifest)
    y, s = tidy["anomaly"].to_numpy()[is_test], scores[is_test]
    flagged = s >= result["threshold"]
    assert result["test"]["precision"] == pytest.approx(precision_score(y, flagged, zero_division=0))
    assert result["test"]["recall"] == pytest.approx(recall_score(y, flagged))
    assert result["test"]["f1"] == pytest.approx(f1_score(y, flagged))
    assert result["test"]["pr_auc"] == pytest.approx(average_precision_score(y, s))
    best_on_test = max(f1_score(y, s >= t) for t in np.unique(s))
    assert result["test"]["f1"] < best_on_test - 0.01, \
        "reported test F1 equals the best achievable on test: was the threshold tuned there?"


def test_per_family_metrics_use_only_that_family(benchmark, case):
    tidy, scores, manifest = case
    _, is_test = _masks(tidy, manifest)
    result = benchmark.evaluate_scores(tidy, scores, manifest)
    for family, part in result["test_by_family"].items():
        m = is_test & (tidy["family"] == family).to_numpy()
        assert part["pr_auc"] == pytest.approx(average_precision_score(tidy["anomaly"].to_numpy()[m], scores[m]))


def test_burn_in_rows_are_excluded_everywhere(benchmark, case):
    tidy, scores, manifest = case
    burn_in = 30
    reference = benchmark.evaluate_scores(tidy, scores, manifest, burn_in=burn_in)
    early = (tidy["t"] < burn_in).to_numpy()
    wild = scores.copy()
    wild[early] = 1e6
    altered = tidy.copy()
    altered.loc[early, "anomaly"] = 1 - altered.loc[early, "anomaly"]
    result = benchmark.evaluate_scores(altered, wild, manifest, burn_in=burn_in)
    assert result["threshold"] == pytest.approx(reference["threshold"])
    assert result["test"]["pr_auc"] == pytest.approx(reference["test"]["pr_auc"])
    assert result["dev"]["pr_auc"] == pytest.approx(reference["dev"]["pr_auc"])


def test_reference_recording_is_not_evaluated(benchmark, case):
    tidy, scores, manifest = case
    reference_rows = (tidy["family"] == "anomaly-free").to_numpy()
    wild = scores.copy()
    wild[reference_rows] = 1e6
    a = benchmark.evaluate_scores(tidy, scores, manifest)
    b = benchmark.evaluate_scores(tidy, wild, manifest)
    assert a["threshold"] == pytest.approx(b["threshold"])
    assert a["test"]["f1"] == pytest.approx(b["test"]["f1"])
