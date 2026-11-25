import numpy as np
import pytest

from ess import effective_sample_size


def ar1(phi, n, seed):
    rng = np.random.default_rng(seed)
    x = np.zeros(n + 200)
    e = rng.standard_normal(n + 200)
    for t in range(1, n + 200):
        x[t] = phi * x[t - 1] + e[t]
    return x[200:]


def test_white_noise_is_about_n():
    x = np.random.default_rng(0).standard_normal(20000)
    # the sum of 20 noisy lags (each sd about 1/sqrt(n)) moves the estimate by several per cent
    assert effective_sample_size(x, 20) == pytest.approx(20000, rel=0.2)


def test_ar1_matches_formula():
    n, phi = 50000, 0.8
    assert effective_sample_size(ar1(phi, n, 1), 60) == pytest.approx(n * (1 - phi) / (1 + phi), rel=0.15)


def test_rejects_bad_input():
    with pytest.raises(ValueError):
        effective_sample_size(np.ones(10), 2)
    with pytest.raises(ValueError):
        effective_sample_size(np.arange(5.0), 5)
