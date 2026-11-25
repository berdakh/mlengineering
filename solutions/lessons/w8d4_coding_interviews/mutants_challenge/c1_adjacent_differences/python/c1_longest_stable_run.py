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
    best_start, best_len, left = 0, 0, 0
    for right in range(len(values)):
        if right > 0 and abs(values[right] - values[right - 1]) > tolerance:
            left = right
        if right - left + 1 > best_len:
            best_start, best_len = left, right - left + 1
    return best_start, best_len
