"""WRONG: the expiry test is off by one, so the maximum is dropped one push too early."""
from collections import deque


class RollingStats:
    def __init__(self, window: int):
        if window < 1:
            raise ValueError("window must be >= 1")
        self._window = window
        self._values: deque[float] = deque()
        self._sum = 0.0
        # Monotonic deque of (index, value), values non-increasing from left to right.
        # The left end is always the maximum of the current window.
        self._maxima: deque[tuple[int, float]] = deque()
        self._n_pushed = 0

    def push(self, x: float) -> None:
        self._values.append(x)
        self._sum += x
        # Anything smaller than x and older than x can never be the maximum again.
        while self._maxima and self._maxima[-1][1] < x:
            self._maxima.pop()
        self._maxima.append((self._n_pushed, x))
        self._n_pushed += 1
        if len(self._values) > self._window:
            self._sum -= self._values.popleft()
            oldest_valid = self._n_pushed - self._window
            if self._maxima[0][0] <= oldest_valid:
                self._maxima.popleft()

    def __len__(self) -> int:
        return len(self._values)

    def mean(self) -> float:
        if not self._values:
            raise ValueError("no values")
        return self._sum / len(self._values)

    def max(self) -> float:
        if not self._values:
            raise ValueError("no values")
        return self._maxima[0][1]
