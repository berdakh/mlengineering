"""WRONG (too slow): correct results, but max() scans the window on every call: O(window)."""
from collections import deque


class RollingStats:
    def __init__(self, window: int):
        if window < 1:
            raise ValueError("window must be >= 1")
        self._values = deque(maxlen=window)

    def push(self, x: float) -> None:
        self._values.append(x)

    def __len__(self) -> int:
        return len(self._values)

    def mean(self) -> float:
        if not self._values:
            raise ValueError("no values")
        return sum(self._values) / len(self._values)

    def max(self) -> float:
        if not self._values:
            raise ValueError("no values")
        return max(self._values)
