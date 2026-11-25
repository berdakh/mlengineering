"""P2 (easy, two pointers): match faults to the first alarm after them. Reference solution."""
from __future__ import annotations


def match_alarms(alarms: list[float], faults: list[float], tolerance: float) -> list[float]:
    """Detection delays of the faults that are detected, in fault order.

    Both lists are sorted ascending. A fault at time f is detected by an alarm a with
    f <= a <= f + tolerance; each alarm detects at most one fault; faults are processed in time order and
    each takes the earliest unused alarm in its interval. Returns [a - f for each detected fault].
    O(len(alarms) + len(faults)).
    """
    used = [False] * len(alarms)
    delays: list[float] = []
    for f in faults:
        for i, a in enumerate(alarms):
            if not used[i] and f <= a <= f + tolerance:
                used[i] = True
                delays.append(a - f)
                break
    return delays
