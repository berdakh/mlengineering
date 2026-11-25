"""simulate_max(k, sigma, n_rep, seed, rho=0.0): Monte-Carlo mean of the maximum of k correlated errors."""
import math

import pytest

N = 40_000


def test_reproducible_under_seed(optimism):
    assert optimism.simulate_max(20, 1.0, 5000, seed=1) == optimism.simulate_max(20, 1.0, 5000, seed=1)
    assert optimism.simulate_max(20, 1.0, 5000, seed=1) != optimism.simulate_max(20, 1.0, 5000, seed=2)


def test_one_candidate_has_no_optimism(optimism):
    assert abs(optimism.simulate_max(1, 1.0, N, seed=0)) < 0.02


@pytest.mark.parametrize("k, expected", [(2, 0.5642), (10, 1.5388), (50, 2.2491)])
def test_independent_case_matches_known_expected_maxima(optimism, k, expected):
    """E[max of k standard normals]: 1/sqrt(pi) for k=2; 1.5388 for k=10; 2.2491 for k=50."""
    assert optimism.simulate_max(k, 1.0, N, seed=0) == pytest.approx(expected, abs=0.03)


def test_scales_linearly_with_sigma_and_stays_below_the_bound(optimism):
    one, small = optimism.simulate_max(30, 1.0, N, seed=3), optimism.simulate_max(30, 0.02, N, seed=3)
    assert small == pytest.approx(0.02 * one, rel=0.03)
    assert small < 0.02 * math.sqrt(2 * math.log(30))


@pytest.mark.parametrize("rho", [0.3, 0.7, 0.95])
def test_shared_noise_shrinks_the_optimism_by_sqrt_one_minus_rho(optimism, rho):
    independent = optimism.simulate_max(40, 1.0, N, seed=5)
    correlated = optimism.simulate_max(40, 1.0, N, seed=6, rho=rho)
    assert correlated == pytest.approx(math.sqrt(1 - rho) * independent, abs=0.04)


def test_fully_shared_noise_has_no_optimism(optimism):
    assert abs(optimism.simulate_max(40, 1.0, N, seed=7, rho=1.0)) < 0.02
