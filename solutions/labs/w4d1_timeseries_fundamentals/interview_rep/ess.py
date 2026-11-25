"""Interview rep reference: effective sample size of an autocorrelated series."""
from __future__ import annotations

import numpy as np


def effective_sample_size(x, max_lag: int) -> float:
    """n / (1 + 2 * sum_{k=1}^{max_lag} r_k), clipped to [1, n].

    Unreliable for short series: r_k is noisy (sd about 1/sqrt(n)) and the sum of many noisy lags can
    be large in either direction; truncating at a small max_lag underestimates long memory.
    """
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 3 or not 1 <= max_lag < n:
        raise ValueError("need n >= 3 and 1 <= max_lag < n")
    d = x - x.mean()
    denom = d @ d
    if denom == 0:
        raise ValueError("constant series")
    r = np.array([d[k:] @ d[:-k] / denom for k in range(1, max_lag + 1)])
    return float(np.clip(n / (1.0 + 2.0 * r.sum()), 1.0, n))
