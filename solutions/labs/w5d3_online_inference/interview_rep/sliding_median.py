"""Interview rep (w5d3): median of the last w values of a stream. Reference answer.

Two answers are worth knowing:
* ``SlidingMedian`` keeps a ring buffer (for eviction order) plus a sorted list (for the median).
  ``bisect`` finds positions in O(log w) but list insert/delete shift elements: O(w) per update,
  which is fast in practice for w up to a few thousand (memmove of pointers).
* ``SlidingMedianHeaps``: two heaps with lazy deletion, O(log w) amortised per update. More code,
  more ways to be wrong; say you would write it only if w is large and profiling says so.
"""
from __future__ import annotations

import heapq
from bisect import bisect_left, insort
from collections import defaultdict, deque


class SlidingMedian:
    def __init__(self, w: int):
        if w < 1:
            raise ValueError("w must be >= 1")
        self.w = w
        self.ring: deque[float] = deque()
        self.sorted: list[float] = []

    def push(self, x: float) -> float | None:
        """Add x; return the median of the last w values, or None until w values have arrived."""
        self.ring.append(x)
        insort(self.sorted, x)
        if len(self.ring) > self.w:
            old = self.ring.popleft()
            del self.sorted[bisect_left(self.sorted, old)]
        if len(self.ring) < self.w:
            return None
        mid = self.w // 2
        return self.sorted[mid] if self.w % 2 else (self.sorted[mid - 1] + self.sorted[mid]) / 2.0


class SlidingMedianHeaps:
    """lo = max-heap (negated) holds the smaller half; hi = min-heap holds the larger half."""

    def __init__(self, w: int):
        if w < 1:
            raise ValueError("w must be >= 1")
        self.w, self.ring = w, deque()
        self.lo: list[float] = []
        self.hi: list[float] = []
        self.delayed: defaultdict[float, int] = defaultdict(int)
        self.lo_size = self.hi_size = 0          # sizes WITHOUT lazily deleted items

    def _prune(self, heap: list[float], sign: int) -> None:
        while heap and self.delayed[sign * heap[0]]:
            self.delayed[sign * heap[0]] -= 1
            heapq.heappop(heap)

    def _rebalance(self) -> None:
        if self.lo_size > self.hi_size + 1:
            heapq.heappush(self.hi, -heapq.heappop(self.lo))
            self.lo_size, self.hi_size = self.lo_size - 1, self.hi_size + 1
            self._prune(self.lo, -1)
        elif self.lo_size < self.hi_size:
            heapq.heappush(self.lo, -heapq.heappop(self.hi))
            self.lo_size, self.hi_size = self.lo_size + 1, self.hi_size - 1
            self._prune(self.hi, 1)

    def push(self, x: float) -> float | None:
        self.ring.append(x)
        if not self.lo or x <= -self.lo[0]:
            heapq.heappush(self.lo, -x)
            self.lo_size += 1
        else:
            heapq.heappush(self.hi, x)
            self.hi_size += 1
        if len(self.ring) > self.w:
            old = self.ring.popleft()
            self.delayed[old] += 1
            if old <= -self.lo[0]:
                self.lo_size -= 1
                self._prune(self.lo, -1)
            else:
                self.hi_size -= 1
                self._prune(self.hi, 1)
        self._rebalance()
        self._prune(self.lo, -1)
        self._prune(self.hi, 1)
        if len(self.ring) < self.w:
            return None
        return -self.lo[0] if self.w % 2 else (-self.lo[0] + self.hi[0]) / 2.0
