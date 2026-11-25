import numpy as np
import pytest

from split import best_split


def test_perfectly_separable_feature():
    x = [5.0, 1.0, 3.0, 8.0, 7.0, 2.0]
    y = [1, 0, 0, 1, 1, 0]
    threshold, impurity = best_split(x, y)
    assert threshold == pytest.approx(4.0) and impurity == pytest.approx(0.0)


def test_matches_brute_force_with_ties():
    rng = np.random.default_rng(0)
    x = rng.integers(0, 15, 300).astype(float)
    y = (x + rng.normal(0, 4, 300) > 7).astype(int)

    def brute(t):
        left, right = y[x <= t], y[x > t]
        g = lambda a: 2 * a.mean() * (1 - a.mean())  # noqa: E731
        return (len(left) * g(left) + len(right) * g(right)) / len(y)
    values = np.unique(x)
    candidates = (values[1:] + values[:-1]) / 2
    best = min(candidates, key=brute)
    threshold, impurity = best_split(x, y)
    assert threshold == pytest.approx(best) and impurity == pytest.approx(brute(best))


def test_constant_feature_has_no_split():
    with pytest.raises(ValueError):
        best_split([2.0, 2.0, 2.0], [0, 1, 0])
