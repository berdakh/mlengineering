"""Turn a per-sample anomaly score into discrete events."""
from __future__ import annotations

import numpy as np


def detect_events(score, threshold: float, min_samples: int = 1, merge_gap: int = 0) -> list[tuple[int, int]]:
    """Return events as half-open sample intervals ``(start, stop)``.

    See the challenge README for the full specification.
    """
    s = np.asarray(score, dtype=float)
    if s.ndim != 1:
        raise ValueError("score must be one-dimensional")
    if min_samples < 1:
        raise ValueError("min_samples must be >= 1")
    if merge_gap < 0:
        raise ValueError("merge_gap must be >= 0")

    above = s > threshold  # NaN compares False: a missing score is never 'above'

    # 1. maximal runs of consecutive above-threshold samples
    runs: list[tuple[int, int]] = []
    start = None
    for i, flag in enumerate(above):
        if flag and start is None:
            start = i
        elif not flag and start is not None:
            runs.append((start, i))
            start = None
    if start is not None:
        runs.append((start, len(s)))

    # 2. merge runs separated by at most merge_gap below-threshold samples
    merged: list[tuple[int, int]] = []
    for run in runs:
        if merged and run[0] - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], run[1])
        else:
            merged.append(run)

    # 3. discard events that are still too short after merging
    return [(a, b) for a, b in merged if b - a >= min_samples]
