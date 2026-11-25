"""Interview rep reference: best Gini split of one numeric feature, O(n log n)."""
from __future__ import annotations

import numpy as np


def best_split(x, y) -> tuple[float, float]:
    """Return (threshold, weighted Gini) of the best split ``x <= threshold`` vs ``x > threshold``.

    Thresholds are midpoints between consecutive distinct sorted values. Raises ValueError when no split
    exists (fewer than two distinct values).
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=int)
    order = np.argsort(x, kind="stable")
    xs, ys = x[order], y[order]
    n = len(xs)
    pos_left = np.cumsum(ys)[:-1]                 # positives among the first i+1 rows
    n_left = np.arange(1, n)
    n_right = n - n_left
    pos_right = ys.sum() - pos_left

    def gini(pos, cnt):
        p = pos / cnt
        return 2.0 * p * (1.0 - p)

    impurity = (n_left * gini(pos_left, n_left) + n_right * gini(pos_right, n_right)) / n
    valid = xs[1:] != xs[:-1]                     # cannot split between equal values
    if not valid.any():
        raise ValueError("need at least two distinct values")
    impurity = np.where(valid, impurity, np.inf)
    i = int(np.argmin(impurity))
    return float((xs[i] + xs[i + 1]) / 2.0), float(impurity[i])
