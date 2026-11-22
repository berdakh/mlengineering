"""Checks for flowguard.detectors: behaviour and contracts on SYNTHETIC data, not one implementation."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score


def _auc(y, s):
    return roc_auc_score(y, s)


# ---------------------------------------------------------------- PCA: T2 and Q
def test_q_catches_a_broken_correlation_that_t2_misses(det, correlated):
    m = det.PCADetector(n_components=4).fit(correlated)
    # a moves without b: inside the normal range of each sensor, but the a-b relationship is broken
    broken = pd.DataFrame({"a": [1.0], "b": [-1.0], "c": [0.0], "d": [0.0], "e": [0.0]})
    # a and b move together, far out along the shared direction: unusual size, normal structure
    along = pd.DataFrame({"a": [4.5], "b": [4.5], "c": [0.0], "d": [0.0], "e": [0.0]})
    assert m.score_q(broken)[0] > m.q_limit_ > m.score_q(along)[0]
    assert m.score_t2(along)[0] > m.t2_limit_ > m.score_t2(broken)[0]


def test_pca_limits_are_99th_percentiles_of_the_fit_rows(det, correlated):
    m = det.PCADetector(n_components=2).fit(correlated)
    assert np.mean(m.score_q(correlated) > m.q_limit_) == pytest.approx(0.01, abs=0.004)
    assert np.mean(m.score_t2(correlated) > m.t2_limit_) == pytest.approx(0.01, abs=0.004)


def test_pca_variance_rule_chooses_components(det, correlated):
    # standardised variances are about 2 (a+b), 1, 1, 1 and ~0.005: 90% needs 4 components, 35% needs 1
    assert det.PCADetector(variance=0.9).fit(correlated).k_ == 4
    assert det.PCADetector(variance=0.35).fit(correlated).k_ == 1


def test_pca_score_selects_the_statistic(det, correlated):
    x = correlated.iloc[:50]
    assert np.allclose(det.PCADetector(n_components=2, statistic="q").fit(correlated).score(x),
                       det.PCADetector(n_components=2).fit(correlated).score_q(x))
    assert np.allclose(det.PCADetector(n_components=2, statistic="t2").fit(correlated).score(x),
                       det.PCADetector(n_components=2).fit(correlated).score_t2(x))


def test_pca_is_scale_invariant(det, correlated):
    scaled = correlated * [1000.0, 0.001, 5.0, 1.0, 1.0] + 7.0
    x = correlated.iloc[:100]
    xs = scaled.iloc[:100]
    np.testing.assert_allclose(det.PCADetector(n_components=3).fit(correlated).score_q(x),
                               det.PCADetector(n_components=3).fit(scaled).score_q(xs), rtol=1e-6, atol=1e-9)


# ---------------------------------------------------------------- isolation forest
def test_iforest_scores_planted_outliers_higher(det):
    rng = np.random.default_rng(2)
    normal = pd.DataFrame(rng.standard_normal((2000, 3)), columns=list("xyz"))
    probe = pd.DataFrame(np.vstack([rng.standard_normal((200, 3)), rng.standard_normal((20, 3)) * 0.5 + 5.0]),
                         columns=list("xyz"))
    y = np.r_[np.zeros(200), np.ones(20)]
    assert _auc(y, det.IForestDetector(seed=0).fit(normal).score(probe)) > 0.95


def test_iforest_is_deterministic_given_the_seed(det, correlated):
    x = correlated.iloc[:300]
    s1 = det.IForestDetector(seed=3).fit(correlated).score(x)
    s2 = det.IForestDetector(seed=3).fit(correlated).score(x)
    s3 = det.IForestDetector(seed=4).fit(correlated).score(x)
    np.testing.assert_array_equal(s1, s2)
    assert not np.allclose(s1, s3)


# ---------------------------------------------------------------- gradient-boosted trees
def test_gbt_learns_a_nonlinear_label(det, labelled):
    x, y = labelled
    m = det.GBTDetector(seed=0).fit(x.iloc[:3000], y[:3000])
    assert _auc(y[3000:], m.score(x.iloc[3000:])) > 0.95


def test_gbt_requires_labels_and_is_deterministic(det, labelled):
    x, y = labelled
    with pytest.raises((ValueError, TypeError)):
        det.GBTDetector(seed=0).fit(x)
    a = det.GBTDetector(seed=5).fit(x, y).score(x.iloc[:200])
    b = det.GBTDetector(seed=5).fit(x, y).score(x.iloc[:200])
    np.testing.assert_array_equal(a, b)


@pytest.mark.parametrize("bad", ["t", "datetime", "anomaly", "experiment_id", "elapsed_s"])
def test_supervised_detector_refuses_forbidden_columns(det, labelled, bad):
    x, y = labelled
    x = x.copy()
    x[bad] = np.arange(len(x)) if bad != "experiment_id" else "valve1/0"
    with pytest.raises(ValueError):
        det.GBTDetector(seed=0).fit(x, y)


# ---------------------------------------------------------------- contract shared by all detectors
def _all(det):
    return {"pca_q": lambda: det.PCADetector(n_components=2, statistic="q"),
            "pca_t2": lambda: det.PCADetector(n_components=2, statistic="t2"),
            "iforest": lambda: det.IForestDetector(seed=0)}


@pytest.mark.parametrize("name", ["pca_q", "pca_t2", "iforest", "gbt"])
def test_row_scores_do_not_depend_on_the_other_rows_scored(det, correlated, name):
    train = correlated.iloc[:2000]
    if name == "gbt":
        y = (train["c"] > 1.0).astype(int).to_numpy()
        m = det.GBTDetector(seed=0).fit(train, y)
    else:
        m = _all(det)[name]().fit(train)
    probe = correlated.iloc[2000:2300]
    together = m.score(probe)
    shifted = pd.concat([probe, probe * 10.0 + 50.0])          # extra, very unusual rows in the same call
    np.testing.assert_allclose(m.score(shifted)[: len(probe)], together, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(m.score(probe.iloc[::-1])[::-1], together, rtol=1e-9, atol=1e-12)
    assert np.isfinite(together).all() and together.shape == (len(probe),)


@pytest.mark.parametrize("name", ["pca_q", "pca_t2", "iforest"])
def test_fitted_state_comes_from_fit_rows_only(det, correlated, name):
    m = _all(det)[name]().fit(correlated.iloc[:1500])
    probe = correlated.iloc[1500:1600]
    before = m.score(probe)
    m.score(correlated.iloc[1600:] + 100.0)                       # scoring other data must not refit
    np.testing.assert_allclose(m.score(probe), before)
