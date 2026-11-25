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
    hi: deque[int] = deque()
    lo: deque[int] = deque()
    best_start, best_len, left = 0, 0, 0
    for right, x in enumerate(values):
        while hi and values[hi[-1]] <= x:
            hi.pop()
        hi.append(right)
        while lo and values[lo[-1]] >= x:
            lo.pop()
        lo.append(right)
        while values[hi[0]] - values[lo[0]] > tolerance:
            left += 1
            if hi[0] < left:
                hi.popleft()
            if lo[0] < left:
                lo.popleft()
        if right - left + 1 > best_len:
            best_start, best_len = left, right - left + 1
    return best_start, best_len
