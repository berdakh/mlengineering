"""WRONG: treats the horizon as a number of rows (the pandas rolling(60) habit)."""
import math
import statistics
from collections import deque


class TimeWindowStats:
    def __init__(self, horizon_s: float):
        if horizon_s <= 0:
            raise ValueError
        self._items = deque(maxlen=int(horizon_s))
        self._last = None

    def push(self, t, x):
        if self._last is not None and t < self._last:
            raise ValueError
        self._last = t
        self._items.append(x)

    def mean(self):
        if not self._items:
            raise ValueError
        return sum(self._items) / len(self._items)

    def std(self):
        if not self._items:
            raise ValueError
        return statistics.stdev(self._items) if len(self._items) > 1 else math.nan

    def __len__(self):
        return len(self._items)
