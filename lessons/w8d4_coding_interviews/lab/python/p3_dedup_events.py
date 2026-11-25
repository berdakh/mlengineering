"""P3 (medium, hash map + sliding window): suppress repeated alerts. Starter: implement the function; the docstring is the specification."""
from __future__ import annotations

from typing import Hashable


def dedup_events(events: list[tuple[float, Hashable]], window: float) -> list[tuple[float, Hashable]]:
    """Keep an event unless an event with the same key was KEPT less than `window` earlier.

    events: (t, key) sorted by t (non-decreasing). Kept events are returned in input order.
    Suppressed events do not extend the window: a steady stream every window/2 keeps every other one.
    Required: O(n) time.
    """
    raise NotImplementedError("w8d4: implement this")
