"""flowguard.baselines: the scorer contract, on SYNTHETIC frames with planted structure."""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

import synth


@pytest.fixture(scope="module")
def train():
    return synth.frame(synth.normal(600, seed=1), experiment_id="anomaly-free/anomaly-free", family="anomaly-free")


def _scorers(baselines):
    return {"MaxAbsZScorer": baselines.MaxAbsZScorer, "MahalanobisScorer": baselines.MahalanobisScorer}


@pytest.mark.parametrize("name", ["ConstantScorer", "MaxAbsZScorer", "MahalanobisScorer"])
def test_scores_are_one_finite_float_per_row(baselines, train, name):
    test = synth.shifted_test(200, seed=2)
    fitted = getattr(baselines, name)().fit(train)
    assert fitted is not None, "fit() must return the fitted scorer (return self)"
    scores = np.asarray(fitted.score(test))
    assert scores.shape == (len(test),)
    assert np.isfinite(scores).all()


def test_constant_scorer_is_constant(baselines, train):
    scores = baselines.ConstantScorer().fit(train).score(synth.shifted_test(100, seed=3))
    assert np.ptp(scores) == 0.0


@pytest.mark.parametrize("name", ["MaxAbsZScorer", "MahalanobisScorer"])
@pytest.mark.parametrize("sensor", ["pressure", "flow_rate", "accelerometer1_rms"])
def test_higher_score_means_more_anomalous(baselines, train, name, sensor):
    test = synth.shifted_test(400, seed=4, sensor=sensor, sigmas=6.0)
    scores = _scorers(baselines)[name]().fit(train).score(test)
    auc = roc_auc_score(test["anomaly"], scores)
    assert auc > 0.95, f"{name}: rows shifted by 6 sigma in {sensor} must score higher (ROC AUC was {auc:.3f})"


@pytest.mark.parametrize("name", ["MaxAbsZScorer", "MahalanobisScorer"])
def test_a_row_score_does_not_depend_on_the_other_rows_scored(baselines, train, name):
    """Statistics come from fit(). A scorer that re-standardises on the data it scores fails here."""
    test = synth.shifted_test(300, seed=5)
    scorer = _scorers(baselines)[name]().fit(train)
    full = np.asarray(scorer.score(test))
    np.testing.assert_allclose(scorer.score(test.iloc[200:]), full[200:], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(scorer.score(test.iloc[[7]]), full[[7]], rtol=1e-9, atol=1e-12)


@pytest.mark.parametrize("name", ["MaxAbsZScorer", "MahalanobisScorer"])
def test_fit_ignores_labels(baselines, train, name):
    test = synth.shifted_test(100, seed=6)
    relabelled = train.assign(anomaly=1, changepoint=1)
    a = _scorers(baselines)[name]().fit(train).score(test)
    b = _scorers(baselines)[name]().fit(relabelled).score(test)
    np.testing.assert_allclose(a, b)


@pytest.mark.parametrize("name", ["MaxAbsZScorer", "MahalanobisScorer"])
def test_scores_do_not_depend_on_sensor_units(baselines, train, name):
    """Volts or millivolts: rescaling a sensor in both train and test must not change the scores."""
    test = synth.shifted_test(200, seed=7)
    a = _scorers(baselines)[name]().fit(train).score(test)
    b = _scorers(baselines)[name]().fit(train.assign(voltage=train["voltage"] * 1000.0)).score(
        test.assign(voltage=test["voltage"] * 1000.0))
    np.testing.assert_allclose(a, b, rtol=1e-6)


@pytest.mark.parametrize("name", ["MaxAbsZScorer", "MahalanobisScorer"])
def test_a_sensor_that_never_moved_in_training_does_not_break_scoring(baselines, train, name):
    frozen = train.assign(pressure=0.1)
    scores = np.asarray(_scorers(baselines)[name]().fit(frozen).score(synth.shifted_test(100, seed=8)))
    assert np.isfinite(scores).all()


def test_mahalanobis_catches_a_broken_correlation(baselines):
    """current and voltage move together in training. Test anomalies move them apart by 1.5 sigma
    each: no single sensor is unusual, the combination is."""
    train = synth.correlated(2000, seed=10)
    test = synth.correlated(600, seed=11, break_rows=60)
    maha = roc_auc_score(test["anomaly"], baselines.MahalanobisScorer().fit(train).score(test))
    maxz = roc_auc_score(test["anomaly"], baselines.MaxAbsZScorer().fit(train).score(test))
    assert maha > 0.97, f"Mahalanobis should separate correlation-breaking rows (ROC AUC was {maha:.3f})"
    assert maha > maxz + 0.1, "on this data the multivariate scorer must clearly beat the per-sensor one"


def test_burn_in_scores_calibrates_each_experiment_on_its_own_start(baselines):
    a = synth.frame(synth.normal(150, seed=20), experiment_id="valve1/0")
    b = synth.frame(synth.normal(150, seed=21) + synth.SCALES * 50.0, experiment_id="valve1/1")   # other regime
    tidy = __import__("pandas").concat([a, b], ignore_index=True)
    scores = baselines.burn_in_scores(baselines.MaxAbsZScorer, tidy, 50)
    assert scores.shape == (300,)
    assert np.median(scores[150:]) < 5.0, "experiment 2 must be judged against its own burn-in, not experiment 1"
