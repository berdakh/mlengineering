"""P4 (medium, aggregation + heap): the k noisiest sensors. Reference solution."""
from __future__ import annotations

import heapq
from typing import Hashable, Iterable


def top_k_variance(readings: Iterable[tuple[Hashable, float]], k: int) -> list:
    """The k sensors with the largest population variance of their readings.

    Sensors with fewer than two readings are ignored. Variances that agree to 12 significant digits are
    ties (floating-point noise must not decide the order); ties are broken by sensor id ascending.
    Returns at most k ids, highest variance first. One pass with Welford's update (numerically stable),
    then a heap: O(n + s log k) for n readings and s sensors.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    sums: dict = {}                             # sensor -> [count, sum, sum of squares]
    for sensor, x in readings:
        s = sums.setdefault(sensor, [0, 0.0, 0.0])
        s[0] += 1
        s[1] += x
        s[2] += x * x
    stats = {k: [n, t / n, q - t * t / n] for k, (n, t, q) in sums.items()}
    scored = ((float(f"{s[2] / s[0]:.12g}"), sensor) for sensor, s in stats.items() if s[0] >= 2)
    best = heapq.nsmallest(k, scored, key=lambda vs: (-vs[0], vs[1]))
    return [sensor for _, sensor in best]
