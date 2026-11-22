"""Interview rep reference: interval merging and overlap (see assessment.md, "Interview rep")."""
from __future__ import annotations

Interval = tuple[int, int]      # half-open [start, end)


def merge_intervals(intervals: list[Interval]) -> list[Interval]:
    """Union of half-open intervals as a sorted list of disjoint intervals. O(n log n).

    Touching intervals ([1, 3) and [3, 5)) are merged; empty intervals (start >= end) are ignored.
    """
    merged: list[list[int]] = []
    for start, end in sorted(i for i in intervals if i[0] < i[1]):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def overlap_length(a: list[Interval], b: list[Interval]) -> int:
    """Total length covered by both ``a`` and ``b``. O(n log n + m log m), two pointers after merging."""
    a, b = merge_intervals(a), merge_intervals(b)
    i = j = total = 0
    while i < len(a) and j < len(b):
        lo, hi = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if lo < hi:
            total += hi - lo
        if a[i][1] <= b[j][1]:          # advance whichever interval ends first
            i += 1
        else:
            j += 1
    return total
