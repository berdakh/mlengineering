"""PSI, KS and W1: known answers, agreement with scipy, invariances, empty bins."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import stats as ss


def test_identical_samples_give_zero(drift):
    x = np.random.default_rng(1).normal(size=500)
    assert drift.psi(x, x) == pytest.approx(0.0, abs=1e-12)
    assert drift.ks_stat(x, x) == pytest.approx(0.0, abs=1e-12)
    assert drift.wasserstein1(x, x) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("n,m,seed", [(50, 80, 0), (300, 300, 1), (17, 1000, 2), (1000, 23, 3)])
def test_ks_and_w1_match_scipy_for_unequal_sizes(drift, n, m, seed):
    rng = np.random.default_rng(seed)
    a, b = rng.normal(size=n), rng.normal(0.3, 1.4, size=m)
    assert drift.ks_stat(a, b) == pytest.approx(ss.ks_2samp(a, b).statistic, abs=1e-12)
    assert drift.wasserstein1(a, b) == pytest.approx(ss.wasserstein_distance(a, b), rel=1e-9)


def test_ks_and_w1_handle_ties(drift):
    rng = np.random.default_rng(4)
    a = rng.integers(0, 5, 200).astype(float)
    b = rng.integers(1, 6, 150).astype(float)
    assert drift.ks_stat(a, b) == pytest.approx(ss.ks_2samp(a, b).statistic, abs=1e-12)
    assert drift.wasserstein1(a, b) == pytest.approx(ss.wasserstein_distance(a, b), rel=1e-9)


def test_w1_of_a_shift_is_the_shift_in_data_units(drift):
    x = np.random.default_rng(5).normal(size=50_000)
    assert drift.wasserstein1(x, x + 0.7) == pytest.approx(0.7, rel=1e-9)
    assert drift.wasserstein1(10 * x, 10 * x + 7) == pytest.approx(7.0, rel=1e-9)


def test_ks_is_invariant_to_monotone_transforms(drift):
    rng = np.random.default_rng(6)
    a, b = rng.normal(size=400), rng.normal(0.2, 1.0, size=300)
    assert drift.ks_stat(np.exp(a), np.exp(b)) == pytest.approx(drift.ks_stat(a, b), abs=1e-12)


def test_psi_from_proportions_is_jeffreys_divergence(drift):
    p = np.array([0.1, 0.2, 0.3, 0.4])
    q = np.array([0.25, 0.25, 0.25, 0.25])
    kl = lambda u, v: float(np.sum(u * np.log(u / v)))  # noqa: E731
    expected = kl(q, p) + kl(p, q)
    assert drift.psi_from_proportions(p, q) == pytest.approx(expected, rel=1e-12)
    assert drift.psi_from_proportions(q, p) == pytest.approx(expected, rel=1e-12)


def test_psi_with_an_empty_bin_is_finite_and_uses_eps(drift):
    ref = np.arange(1000, dtype=float)              # deciles at 99.9, 199.8, ...
    cur = np.full(200, 5000.0)                      # every current value in the top bin
    value = drift.psi(ref, cur)
    assert math.isfinite(value), "an empty bin must not give inf or nan (floor the shares at EPS)"
    p = np.full(10, 0.1)
    q = np.full(10, drift.EPS)
    q[-1] = 1.0
    assert value == pytest.approx(float(np.sum((q - p) * np.log(q / p))), rel=1e-6)


def test_psi_uses_reference_quantile_bins(drift):
    rng = np.random.default_rng(7)
    ref = rng.normal(size=10_000)
    same = rng.normal(size=10_000)
    shifted = rng.normal(0.5, 1, size=10_000)
    assert drift.psi(ref, same) < 0.01
    assert 0.2 < drift.psi(ref, shifted) < 0.35, "a 0.5 SD shift gives PSI of about 0.25 with decile bins"
