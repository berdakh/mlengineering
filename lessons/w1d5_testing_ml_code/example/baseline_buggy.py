"""Rolling z-score against a trailing baseline - FIRST VERSION, contains a defect.

Specification
-------------
z[t] = (x[t] - mean(B_t)) / std(B_t),   B_t = x[t-window : t]   (the `window` samples BEFORE t)

* std is the sample standard deviation (ddof=1).
* z[t] is NaN for t < window (no complete baseline yet) and where std(B_t) == 0.
* The baseline must not contain x[t] itself: an anomaly must not dilute its own score.
"""
import numpy as np


def rolling_zscore(x, window: int) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if window < 2:
        raise ValueError("window must be >= 2")
    z = np.full(len(x), np.nan)
    for t in range(window, len(x)):
        baseline = x[t - window + 1 : t + 1]
        sd = baseline.std(ddof=1)
        if sd > 0:
            z[t] = (x[t] - baseline.mean()) / sd
    return z
