"""WRONG: correct values, but recomputes over the whole window on every call (O(window))."""
import math
import statistics
from collections import deque


class TimeWindowStats:
    def __init__(self, horizon_s: float):
        if horizon_s <= 0:
            raise ValueError
        self._h = horizon_s
        self._items = deque()

    def push(self, t, x):
        if self._items and t < self._items[-1][0]:
            raise ValueError
        self._items.append((t, x))
        while self._items[0][0] <= t - self._h:
            self._items.popleft()

    def mean(self):
        if not self._items:
            raise ValueError
        return sum(x for _, x in self._items) / len(self._items)

    def std(self):
        if not self._items:
            raise ValueError
        return statistics.stdev(x for _, x in self._items) if len(self._items) > 1 else math.nan

    def __len__(self):
        return len(self._items)
