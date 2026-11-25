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
    stats: dict = {}                            # sensor -> [count, mean, M2]
    for sensor, x in readings:
        s = stats.get(sensor)
        if s is None:
            stats[sensor] = [1, float(x), 0.0]
            continue
        s[0] += 1
        delta = x - s[1]
        s[1] += delta / s[0]
        s[2] += delta * (x - s[1])
    scored = ((float(f"{s[2] / s[0]:.12g}"), sensor) for sensor, s in stats.items() if s[0] >= 2)
    best = heapq.nsmallest(k, scored, key=lambda vs: (-vs[0], vs[1]))
    return [sensor for _, sensor in best]
