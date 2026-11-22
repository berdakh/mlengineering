"""Tests for the interview rep. Run: python -m pytest solutions/lessons/w5d3_online_inference/interview_rep -q"""
import numpy as np
import pytest

from sliding_median import SlidingMedian, SlidingMedianHeaps


@pytest.mark.parametrize("cls", [SlidingMedian, SlidingMedianHeaps])
@pytest.mark.parametrize("w", [1, 2, 5, 50])
def test_matches_numpy_on_random_data_with_ties(cls, w):
    rng = np.random.default_rng(w)
    xs = rng.integers(0, 10, 2000).astype(float)              # many ties on purpose
    m = cls(w)
    got = [m.push(x) for x in xs]
    assert got[: w - 1] == [None] * (w - 1)
    expected = [float(np.median(xs[i - w + 1: i + 1])) for i in range(w - 1, len(xs))]
    assert got[w - 1:] == pytest.approx(expected)


@pytest.mark.parametrize("cls", [SlidingMedian, SlidingMedianHeaps])
def test_rejects_bad_window(cls):
    with pytest.raises(ValueError):
        cls(0)


def test_robust_to_a_spike_unlike_the_mean():
    m = SlidingMedian(5)
    out = [m.push(x) for x in [10, 10, 10, 1e6, 10, 10]]
    assert out[-1] == 10
