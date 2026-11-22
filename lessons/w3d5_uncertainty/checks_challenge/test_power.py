"""Checks for the power analysis. Differences are SYNTHETIC draws from known distributions."""
from __future__ import annotations

import numpy as np
import pytest
from scipy import stats


def t_test_power(mean: float, sd: float, n: int, alpha: float = 0.05) -> float:
    """Power of the two-sided paired t-test (noncentral t). For normal differences the sign-flip
    permutation test has almost the same power, so this is an independent reference."""
    df = n - 1
    crit = stats.t.ppf(1 - alpha / 2, df)
    nc = mean / sd * np.sqrt(n)
    return float(stats.nct.sf(crit, df, nc) + stats.nct.cdf(-crit, df, nc))


def test_valid_test_under_no_difference(pw):
    rate = pw.power(pw.normal_draw(0.0, 1.0), n_experiments=12, n_sim=1500, seed=1)
    assert 0.02 <= rate <= 0.075, (
        f"with no true difference the rejection rate is {rate:.3f}; a two-sided test at alpha = 0.05 "
        "should reject about 5% of the time")


@pytest.mark.parametrize("mean,sd,n", [(0.5, 1.0, 20), (0.5, 1.0, 40), (0.02, 0.05, 30), (1.0, 1.0, 9)])
def test_power_matches_known_answer(pw, mean, sd, n):
    got = pw.power(pw.normal_draw(mean, sd), n_experiments=n, n_sim=800, seed=2)
    want = t_test_power(mean, sd, n)
    assert got == pytest.approx(want, abs=0.07), f"power {got:.3f}, reference {want:.3f}"


def test_power_grows_with_experiments_and_effect(pw):
    draw = pw.normal_draw(0.3, 1.0)
    p10, p40, p160 = (pw.power(draw, n, n_sim=500, seed=3) for n in (10, 40, 160))
    assert p10 + 0.15 < p40 < p160 - 0.15, (p10, p40, p160)
    weak = pw.power(pw.normal_draw(0.2, 1.0), 30, n_sim=500, seed=3)
    strong = pw.power(pw.normal_draw(0.8, 1.0), 30, n_sim=500, seed=3)
    assert weak + 0.4 < strong


def test_draw_is_asked_for_n_experiments(pw):
    sizes = set()

    def draw(rng, n):
        sizes.add(n)
        return rng.normal(0.5, 1.0, size=n)

    pw.power(draw, n_experiments=17, n_sim=20, seed=0)
    assert sizes == {17}


def test_reproducible_and_seed_dependent(pw):
    draw = pw.normal_draw(0.4, 1.0)
    a = pw.power(draw, 25, n_sim=300, seed=10)
    b = pw.power(draw, 25, n_sim=300, seed=10)
    others = {pw.power(draw, 25, n_sim=300, seed=s) for s in (11, 12, 13)}
    assert a == b, "same seed must give the same power estimate"
    assert others != {a}, "the seed must drive the simulation"


def test_empirical_draw_supports_heavy_tails(pw):
    pool = np.r_[np.full(27, 0.01), [-0.6, 0.5, 0.45]]          # mostly tiny gains, three large swings
    low = pw.power(pw.empirical_draw(pool), 30, n_sim=400, seed=4)
    assert 0.0 <= low <= 0.5
    shifted = pw.power(pw.empirical_draw(pool, shift=0.5), 30, n_sim=400, seed=4)
    assert shifted > 0.95


def test_required_experiments_is_the_smallest_sufficient_candidate(pw):
    draw = pw.normal_draw(0.5, 1.0)                               # t-test power: n=20 -> 0.56, n=40 -> 0.87
    assert pw.required_experiments(draw, [5, 10, 20, 40, 80], target_power=0.8, n_sim=500, seed=5) == 40
    assert pw.required_experiments(pw.normal_draw(3.0, 1.0), [80, 10, 40], target_power=0.8, n_sim=200, seed=5) == 10
    assert pw.required_experiments(pw.normal_draw(0.0, 1.0), [5, 10, 20], target_power=0.8, n_sim=200, seed=5) is None
