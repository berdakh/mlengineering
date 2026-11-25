"""P3 (medium, hash map + sliding window): suppress repeated alerts. Reference solution."""
from __future__ import annotations

from typing import Hashable


def dedup_events(events: list[tuple[float, Hashable]], window: float) -> list[tuple[float, Hashable]]:
    """Keep an event unless an event with the same key was KEPT less than `window` earlier.

    events: (t, key) sorted by t (non-decreasing). Kept events are returned in input order.
    Suppressed events do not extend the window: a steady stream every window/2 keeps every other one.
    O(n) time, O(number of keys) memory.
    """
    last_kept: dict = {}
    kept = []
    for t, key in events:
        prev = last_kept.get(key)
        if prev is None or t - prev >= window:
            kept.append((t, key))
            last_kept[key] = t
    return kept
