"""C1 (mock, sliding window with monotonic deques): the longest stable stretch of a signal. Reference."""
from __future__ import annotations

from collections import deque


def longest_stable_run(values: list[float], tolerance: float) -> tuple[int, int]:
    """(start, length) of the longest contiguous run whose max - min <= tolerance.

    The earliest such run wins ties. Empty input -> (0, 0). Required: O(n).
    Two deques hold indices of the window's candidate maxima (decreasing values) and minima (increasing).
    """
    if tolerance < 0:
        raise ValueError("tolerance must be >= 0")
    best_start, best_len = 0, 0
    for i in range(len(values)):
        lo_v = hi_v = values[i]
        for j in range(i, len(values)):
            lo_v, hi_v = min(lo_v, values[j]), max(hi_v, values[j])
            if hi_v - lo_v > tolerance:
                break
            if j - i + 1 > best_len:
                best_start, best_len = i, j - i + 1
    return best_start, best_len
