"""Reference for the w2d5 interview rep."""
from __future__ import annotations

from collections import deque


def sliding_max(values, w: int) -> list:
    """Maximum of each length-w window, O(n): a deque of indices whose values are decreasing."""
    if w < 1:
        raise ValueError("w must be >= 1")
    candidates: deque[int] = deque()  # indices; values[candidates] strictly decreasing
    out = []
    for i, v in enumerate(values):
        while candidates and values[candidates[-1]] <= v:
            candidates.pop()            # can never be a maximum again: older and not larger
        candidates.append(i)
        if candidates[0] <= i - w:
            candidates.popleft()        # fell out of the window
        if i >= w - 1:
            out.append(values[candidates[0]])
    return out


class StreamingStats:
    """Mean and population variance of the last w values, O(1) per update, O(w) memory."""

    def __init__(self, w: int):
        if w < 1:
            raise ValueError("w must be >= 1")
        self.w = w
        self.buffer: deque[float] = deque()
        self.total = 0.0
        self.total_sq = 0.0

    def update(self, x: float) -> tuple[float, float]:
        self.buffer.append(x)
        self.total += x
        self.total_sq += x * x
        if len(self.buffer) > self.w:
            old = self.buffer.popleft()
            self.total -= old
            self.total_sq -= old * old
        n = len(self.buffer)
        mean = self.total / n
        # Numerical risk: sum of squares minus square of sum cancels catastrophically when the
        # mean is large relative to the spread, and add/subtract drift accumulates over long streams.
        variance = max(self.total_sq / n - mean * mean, 0.0)
        return mean, variance
