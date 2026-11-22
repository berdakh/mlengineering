"""Reference for set 4, C3: mean and sample std over the trailing window (t - horizon, t]."""
import math
from collections import deque


class TimeWindowStats:
    def __init__(self, horizon_s: float):
        if horizon_s <= 0:
            raise ValueError("horizon_s must be positive")
        self._horizon = horizon_s
        self._items = deque()        # (t, x), oldest on the left
        self._mean = 0.0             # Welford-style running mean and sum of squared deviations
        self._m2 = 0.0

    def push(self, t: float, x: float) -> None:
        if self._items and t < self._items[-1][0]:
            raise ValueError("timestamps must be non-decreasing")
        self._add(x)
        self._items.append((t, x))
        while self._items[0][0] <= t - self._horizon:
            _, old = self._items.popleft()
            self._remove(old)

    def _add(self, x: float) -> None:
        n = len(self._items) + 1
        delta = x - self._mean
        self._mean += delta / n
        self._m2 += delta * (x - self._mean)

    def _remove(self, x: float) -> None:
        n = len(self._items)         # count after removal
        if n == 0:
            self._mean, self._m2 = 0.0, 0.0
            return
        delta = x - self._mean
        self._mean -= delta / n
        self._m2 -= delta * (x - self._mean)

    def mean(self) -> float:
        if not self._items:
            raise ValueError("no values")
        return self._mean

    def std(self) -> float:
        if not self._items:
            raise ValueError("no values")
        if len(self._items) < 2:
            return float("nan")
        return math.sqrt(max(self._m2, 0.0) / (len(self._items) - 1))

    def __len__(self) -> int:
        return len(self._items)
