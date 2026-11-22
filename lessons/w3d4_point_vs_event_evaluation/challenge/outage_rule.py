"""Part B: your matching rule for short outages with late, jittery log labels. CHALLENGE STARTER.

Build it from flowguard.evaluation (match_events, detection_delay, delay_summary, ...). You may
transform the logged events before matching. Return a dict of whatever you decide to report; the
harness in outages.py prints it for both detectors. Defend every choice in OUTAGE_RULE.md.
"""
from __future__ import annotations

import _paths  # noqa: F401


def score_outages(logged, alarms, times) -> dict:
    raise NotImplementedError("TODO: design and implement your matching rule")
