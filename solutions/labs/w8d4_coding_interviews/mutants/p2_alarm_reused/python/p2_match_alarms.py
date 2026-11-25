"""P2 (easy, two pointers): match faults to the first alarm after them. Reference solution."""
from __future__ import annotations


def match_alarms(alarms: list[float], faults: list[float], tolerance: float) -> list[float]:
    """Detection delays of the faults that are detected, in fault order.

    Both lists are sorted ascending. A fault at time f is detected by an alarm a with
    f <= a <= f + tolerance; each alarm detects at most one fault; faults are processed in time order and
    each takes the earliest unused alarm in its interval. Returns [a - f for each detected fault].
    O(len(alarms) + len(faults)).
    """
    delays: list[float] = []
    i = 0
    for f in faults:
        while i < len(alarms) and alarms[i] < f:
            i += 1                              # alarms before the fault can never be used later
        if i < len(alarms) and alarms[i] <= f + tolerance:
            delays.append(alarms[i] - f)
    return delays
