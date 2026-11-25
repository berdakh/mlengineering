"""Part B reference: a matching rule for short outages with late, jittery log labels.

Decisions (defended in OUTAGE_RULE.md):
* early tolerance 8 rows: the log is known to lag the outage by up to 8 s, so an alarm up to 8 s
  before the LOGGED onset is on time, not early;
* grace period 15 rows after the logged end: outages last 3-20 s, so a correct alarm can start
  after a short outage is over; the window never extends into the next logged outage;
* one alarm can be the hit for one outage only (inherited from match_events: an alarm has one start);
* delay is reported, with the warning that the labels cannot resolve anything below about 8 s.
"""
from __future__ import annotations

import numpy as np

import _paths  # noqa: F401
from flowguard.evaluation import delay_summary, detection_delay, match_events

EARLY_TOLERANCE = 8
GRACE = 15


def score_outages(logged, alarms, times) -> dict:
    windows = []
    for k, (s, e) in enumerate(logged):
        next_start = logged[k + 1][0] - EARLY_TOLERANCE if k + 1 < len(logged) else len(times)
        windows.append((s, max(e, min(e + GRACE, next_start))))
    labels = match_events(windows, alarms, early_tolerance=EARLY_TOLERANCE)["pred_label"]
    delays = detection_delay(windows, alarms, times, early_tolerance=EARLY_TOLERANCE)
    in_window = np.zeros(len(times), dtype=bool)
    for s, e in windows:
        in_window[max(0, s - EARLY_TOLERANCE):e] = True
    quiet_hours = float((~in_window).sum()) / 3600.0          # 1 Hz, no gaps in this simulation
    return {"events found": f"{int(np.isfinite(delays).sum())}/{len(logged)}", "alarms": len(alarms),
            "false alarms": labels.count("false_alarm"),
            "false alarms/day": round(24 * labels.count("false_alarm") / quiet_hours, 1),
            "median delay s": delay_summary(delays)["median"],
            "delay resolution s": EARLY_TOLERANCE}
