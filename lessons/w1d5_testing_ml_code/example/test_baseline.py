"""Worked example: tests written from the specification of rolling_zscore.

    python -m pytest lessons/w1d5_testing_ml_code/example -q                      # correct version
    ZSCORE_IMPL=buggy python -m pytest lessons/w1d5_testing_ml_code/example -q    # first version
"""
import os

import numpy as np
import pytest

if os.environ.get("ZSCORE_IMPL") == "buggy":
    from baseline_buggy import rolling_zscore
else:
    from baseline import rolling_zscore


@pytest.fixture
def noise() -> np.ndarray:
    return np.random.default_rng(0).standard_normal(200)


def test_known_answer_computed_by_hand():
    # Baseline for t=4 is [1, 2, 3, 4]: mean 2.5, sample std sqrt(5/3).
    z = rolling_zscore([1.0, 2.0, 3.0, 4.0, 10.0], window=4)
    assert z[4] == pytest.approx((10.0 - 2.5) / np.sqrt(5.0 / 3.0), rel=1e-12)


def test_warm_up_region_is_nan_and_rest_is_finite(noise):
    z = rolling_zscore(noise, window=20)
    assert np.isnan(z[:20]).all()
    assert np.isfinite(z[20:]).all()


def test_flat_baseline_gives_nan_not_infinity():
    z = rolling_zscore([3.0, 3.0, 3.0, 3.0, 9.0], window=4)
    assert np.isnan(z[4])


@pytest.mark.parametrize("scale, offset", [(2.0, 0.0), (1.0, 50.0), (0.01, -3.0)])
def test_invariant_to_positive_affine_transform(noise, scale, offset):
    # A z-score has no units: changing gain or DC offset of the sensor must not change it.
    np.testing.assert_allclose(
        rolling_zscore(scale * noise + offset, 20)[20:], rolling_zscore(noise, 20)[20:], rtol=1e-7, atol=1e-9
    )


def test_causal_future_samples_do_not_change_past_scores(noise):
    altered = noise.copy()
    altered[120:] += 1000.0
    np.testing.assert_array_equal(rolling_zscore(altered, 20)[:120], rolling_zscore(noise, 20)[:120])


def test_spike_does_not_dilute_its_own_score(noise):
    # Property stated in the spec: the score at t depends on x[t] only through the numerator,
    # so making the spike 10x larger makes its deviation from the baseline 10x larger.
    t, window = 100, 20
    small, large = noise.copy(), noise.copy()
    mean = noise[t - window : t].mean()
    small[t] = mean + 5.0
    large[t] = mean + 50.0
    assert rolling_zscore(large, window)[t] == pytest.approx(10 * rolling_zscore(small, window)[t], rel=1e-9)


def test_window_too_small_is_rejected():
    with pytest.raises(ValueError, match="window"):
        rolling_zscore([1.0, 2.0, 3.0], window=1)
