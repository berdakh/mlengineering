"""Checks for flowguard.forecast. They test behaviour (known answers, invariants, causality), not code."""
from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------- Task 1: acf
def test_acf_lag0_is_one_and_length(fc, ar):
    r = fc.acf(ar([0.5], 2000), 7)
    assert len(r) == 8 and r[0] == pytest.approx(1.0)


def test_acf_ar1_matches_theory_even_with_large_mean(fc, ar):
    # for AR(1), rho_k = phi^k; the series mean (40) must not leak into the estimate
    r = fc.acf(ar([0.8], 20000, mean=40.0, seed=1), 3)
    assert r[1:] == pytest.approx([0.8, 0.64, 0.512], abs=0.03)


def test_acf_white_noise_is_near_zero(fc):
    x = np.random.default_rng(3).standard_normal(20000)
    assert np.all(np.abs(fc.acf(x, 10)[1:]) < 0.03)


def test_acf_rejects_constant_and_bad_lag(fc):
    with pytest.raises(ValueError):
        fc.acf(np.ones(50), 3)
    with pytest.raises(ValueError):
        fc.acf(np.arange(10.0), 10)


# ---------------------------------------------------------------- Task 2: naive forecasters
def test_naive_predicts_previous_value(fc):
    x = np.array([3.0, 5.0, 4.0, 9.0])
    pred = fc.NaiveForecaster().fit(x).predict(x)
    assert np.isnan(pred[0]) and pred[1:] == pytest.approx([3.0, 5.0, 4.0])


def test_seasonal_naive_uses_one_period_ago(fc):
    x = np.arange(10.0) ** 2
    pred = fc.SeasonalNaiveForecaster(3).fit(x).predict(x)
    assert np.isnan(pred[:3]).all()
    assert pred[3:] == pytest.approx(x[:-3])


# ---------------------------------------------------------------- Task 3: AR(p)
def test_ar_recovers_coefficients_and_intercept(fc, ar):
    x = ar([0.6, -0.3], 8000, mean=10.0, seed=4)
    m = fc.ARForecaster(2).fit(x)
    assert m.coef_ == pytest.approx([0.6, -0.3], abs=0.04)
    # c = mean * (1 - sum(phi)) = 10 * 0.7
    assert m.intercept_ == pytest.approx(7.0, abs=0.4)


def test_ar_sigma_is_innovation_scale_not_series_scale(fc, ar):
    # series std is 1/sqrt(1 - 0.81) ~ 2.3; innovations have std 1.5
    x = ar([0.9], 8000, sigma=1.5, seed=5)
    m = fc.ARForecaster(1).fit(x)
    assert m.sigma_ == pytest.approx(1.5, rel=0.05)


def test_correct_order_leaves_white_residuals_wrong_order_does_not(fc, ar):
    x = ar([0.5, 0.35], 10000, seed=6)
    good = fc.ARForecaster(2).fit(x)
    bad = fc.ARForecaster(1).fit(x)
    r_good = (x - good.predict(x))[2:]
    r_bad = (x - bad.predict(x))[2:]
    assert np.all(np.abs(fc.acf(r_good, 5)[1:]) < 0.04)
    assert np.max(np.abs(fc.acf(r_bad, 5)[1:])) > 0.08


@pytest.mark.parametrize("make", ["naive", "seasonal", "ar"])
def test_predictions_never_use_the_present_or_future(fc, ar, make):
    model = {"naive": lambda: fc.NaiveForecaster(),
             "seasonal": lambda: fc.SeasonalNaiveForecaster(4),
             "ar": lambda: fc.ARForecaster(3)}[make]()
    x = ar([0.5], 300, seed=7)
    model.fit(x[:150])
    base = model.predict(x)
    for j in (40, 150, 299):
        y = x.copy()
        y[j:] += 100.0                       # change the value at j and everything after it
        pred = model.predict(y)
        np.testing.assert_allclose(pred[: j + 1], base[: j + 1], equal_nan=True,
                                   err_msg=f"prediction at or before index {j} changed when x[{j}:] changed")


def test_ar_first_p_predictions_are_nan_and_length_matches(fc, ar):
    x = ar([0.5], 200, seed=8)
    pred = fc.ARForecaster(3).fit(x).predict(x)
    assert len(pred) == len(x) and np.isnan(pred[:3]).all() and np.isfinite(pred[3:]).all()


def test_ar_parameters_come_from_fit_data_only(fc, ar):
    train, other = ar([0.8], 3000, seed=9), ar([-0.5], 3000, mean=50.0, seed=10)
    m = fc.ARForecaster(1).fit(train)
    before = (m.coef_.copy(), m.intercept_, m.sigma_)
    m.predict(other)
    assert m.coef_ == pytest.approx(before[0]) and m.intercept_ == before[1] and m.sigma_ == before[2]
    assert m.coef_[0] == pytest.approx(0.8, abs=0.05)


def test_ar_rejects_short_or_nan_series(fc):
    with pytest.raises(ValueError):
        fc.ARForecaster(3).fit(np.arange(6.0))
    with pytest.raises(ValueError):
        fc.ARForecaster(1).fit(np.array([1.0, 2.0, np.nan, 4.0, 5.0, 6.0, 7.0, 8.0]))


# ---------------------------------------------------------------- Task 4: residual scores
def test_residual_scores_are_scale_free(fc, ar):
    x = ar([0.7], 2000, seed=11)
    s1 = fc.residual_scores(fc.ARForecaster(2).fit(x), x)
    s2 = fc.residual_scores(fc.ARForecaster(2).fit(1000.0 * x + 3.0), 1000.0 * x + 3.0)
    np.testing.assert_allclose(s1, s2, rtol=1e-6, equal_nan=True)


def test_residual_scores_flag_a_planted_spike(fc, ar):
    x = ar([0.7], 1000, seed=12)
    m = fc.ARForecaster(1).fit(x[:500])
    y = x.copy()
    y[700] += 8.0
    s = fc.residual_scores(m, y)
    assert np.isnan(s[0]) and np.nanargmax(s) == 700 and s[700] > 5.0


# ---------------------------------------------------------------- Task 5: CUSUM
def test_cusum_known_answer(fc):
    assert fc.cusum([0, 0, 3, 3, 0, -3], k=0.5) == pytest.approx([0, 0, 2.5, 5.0, 4.5, 2.5])


def test_cusum_skips_nan_and_rejects_negative_k(fc):
    assert fc.cusum([np.nan, 2.0, np.nan], k=0.5) == pytest.approx([0.0, 1.5, 1.5])
    with pytest.raises(ValueError):
        fc.cusum([0.0, 1.0], k=-1.0)


def test_cusum_detects_a_one_sigma_shift_with_the_expected_delay(fc):
    # theory: after a shift of delta (in sigma units) the statistic grows by about delta - k per step,
    # so with delta = 1, k = 0.5, h = 5 the alarm comes about 10 samples after onset
    delays = []
    for seed in range(40):
        z = np.random.default_rng(seed).standard_normal(400)
        z[200:] += 1.0
        stat = fc.cusum(z, k=0.5)
        first = np.flatnonzero(stat[200:] > 5.0)
        delays.append(first[0] if len(first) else 999)
    assert 6 <= np.median(delays) <= 20


def test_cusum_rarely_alarms_on_noise(fc):
    # two-sided k = 0.5, h = 5: the in-control run length averages a few hundred samples, so about 1 in
    # 10 runs of 50 samples alarms; a chart that ignores k alarms in most of them
    alarms = 0
    for seed in range(20):
        stat = fc.cusum(np.random.default_rng(100 + seed).standard_normal(50), k=0.5)
        alarms += bool((stat > 5.0).any())
    assert alarms <= 6


# ---------------------------------------------------------------- the given per-experiment helper
def test_burn_in_scores_are_causal_and_per_experiment(fc, tidy_factory):
    tidy = tidy_factory()
    sensors = ["flow_rate", "pressure"]
    base = fc.burn_in_forecast_scores(tidy, lambda: fc.ARForecaster(2), sensors, n_burn=60)
    changed = tidy.copy()
    late = (changed["experiment_id"] == "valve1/1") & (changed["t"] >= 120)
    changed.loc[late, "flow_rate"] += 50.0
    after = fc.burn_in_forecast_scores(changed, lambda: fc.ARForecaster(2), sensors, n_burn=60)
    untouched = ~((changed["experiment_id"] == "valve1/1") & (changed["t"] >= 120)).to_numpy()
    np.testing.assert_allclose(after[untouched], base[untouched], equal_nan=True)
    assert np.nanmax(after[~untouched]) > 10.0
