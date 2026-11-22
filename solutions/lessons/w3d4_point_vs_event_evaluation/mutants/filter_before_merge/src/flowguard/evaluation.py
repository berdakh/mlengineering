"""Event-level evaluation of a detector. One sequence = one experiment, in time order.

Conventions (the checks rely on them)
-------------------------------------
* An **event** is a half-open pair of row indices ``(start, end)``: rows ``start .. end-1`` are in
  the event, so its length in rows is ``end - start`` and ``binary[start:end]`` is all ones.
* An **alarm** is a predicted event. An alarm is *news at the row where it starts*; everything this
  module decides about an alarm is decided from its start.
* Matching rule (``match_events``): an alarm **detects** a true event when it starts inside it, or
  at most ``early_tolerance`` rows before its start (allowance for an imprecisely labelled onset).
  - the earliest alarm that detects a true event is a ``"hit"``;
  - later alarms that start inside an already detected event are ``"redundant"``: the same fault
    announced again. They are neither true positives nor false alarms;
  - an alarm that detects nothing is a ``"false_alarm"``. That includes an alarm that started in
    normal operation and is still on when a true event begins: it told the operator nothing about
    the onset, and it does not detect that event.
* Detection delay is measured from the true start to the moment the hit is raised (its start, plus
  the confirmation rows a minimum-duration filter needs), never negative, and is ``inf`` for a missed
  event (the delay is censored: all we know is that it exceeds the recording).
* Time comes from ``times`` (seconds as numbers, or datetimes), never from counting rows.
"""
from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd

Event = tuple[int, int]


# --------------------------------------------------------------------------- events from flags
def extract_events(binary, min_duration: int = 1, merge_gap: int = 0) -> list[Event]:
    """Runs of ones in ``binary`` as ``(start, end)`` pairs, end exclusive, in time order.

    Post-processing, applied in this order:
    1. runs separated by ``merge_gap`` or fewer zeros are merged into one event;
    2. events shorter than ``min_duration`` rows are then dropped.
    """
    if min_duration < 1 or merge_gap < 0:
        raise ValueError("min_duration must be >= 1 and merge_gap >= 0")
    flags = np.asarray(binary).astype(bool).ravel()
    if flags.size == 0:
        return []
    edges = np.diff(np.r_[0, flags.astype(np.int8), 0])
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)
    merged: list[list[int]] = []
    for s, e in zip(starts.tolist(), ends.tolist()):
        if e - s < min_duration:
            continue
        if merged and s - merged[-1][1] <= merge_gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if e - s >= min_duration]


def point_adjust(y_true, y_pred) -> np.ndarray:
    """The "point-adjust" protocol: if ANY row of a true event is flagged, mark the WHOLE event as
    flagged. Rows outside true events are left unchanged. Returns a new 0/1 integer array.

    Implemented to demonstrate how much this protocol inflates point-wise scores. Do not report
    point-adjusted numbers as detector performance.
    """
    y = np.asarray(y_true).astype(int).ravel()
    p = np.asarray(y_pred).astype(int).ravel().copy()
    if y.shape != p.shape:
        raise ValueError("y_true and y_pred differ in length")
    for s, e in extract_events(y):
        if p[s:e].any():
            p[s:e] = 1
    return p


# --------------------------------------------------------------------------- matching
def match_events(true_events: Sequence[Event], pred_events: Sequence[Event], early_tolerance: int = 0) -> dict:
    """Match alarms to true events under the rule in the module docstring.

    Returns ``{"first_detection": [...], "pred_label": [...]}`` where
    * ``first_detection[k]`` is the start row of the hit for true event ``k``, or ``None`` if missed;
    * ``pred_label[j]`` is ``"hit"``, ``"redundant"`` or ``"false_alarm"`` for alarm ``j``.
    """
    if early_tolerance < 0:
        raise ValueError("early_tolerance must be >= 0")
    first: list[int | None] = [None] * len(true_events)
    hit_by: list[int | None] = [None] * len(true_events)
    detects_any = [False] * len(pred_events)
    for j, (ps, _pe) in enumerate(pred_events):
        for k, (ts, te) in enumerate(true_events):
            if ts - early_tolerance <= ps < te:
                detects_any[j] = True
                if first[k] is None or ps < first[k]:
                    first[k], hit_by[k] = ps, j
    hits = {j for j in hit_by if j is not None}
    labels = ["hit" if j in hits else "redundant" if detects_any[j] else "false_alarm"
              for j in range(len(pred_events))]
    return {"first_detection": first, "pred_label": labels}


def event_recall(true_events, pred_events, early_tolerance: int = 0) -> float:
    """Detected true events / true events. NaN when there are no true events."""
    if not len(true_events):
        return float("nan")
    m = match_events(true_events, pred_events, early_tolerance)
    return sum(d is not None for d in m["first_detection"]) / len(true_events)


def event_precision(true_events, pred_events, early_tolerance: int = 0) -> float:
    """hits / (hits + false alarms); redundant alarms are ignored. NaN when both counts are zero."""
    labels = match_events(true_events, pred_events, early_tolerance)["pred_label"]
    hits, false_alarms = labels.count("hit"), labels.count("false_alarm")
    return hits / (hits + false_alarms) if hits + false_alarms else float("nan")


# --------------------------------------------------------------------------- time
def _seconds(times, n: int | None = None) -> np.ndarray:
    """Timestamps as float seconds. Accepts numbers (already seconds) or datetimes."""
    arr = np.asarray(times)
    if np.issubdtype(arr.dtype, np.datetime64) or arr.dtype == object:
        arr = pd.to_datetime(pd.Series(arr)).to_numpy(dtype="datetime64[ns]")
        return (arr - arr[0]) / np.timedelta64(1, "s") if len(arr) else np.zeros(0)
    return arr.astype(float)


def detection_delay(true_events, pred_events, times=None, early_tolerance: int = 0,
                    confirm_rows: int = 0) -> np.ndarray:
    """One delay per true event, in the unit of ``times`` (seconds), or in rows if ``times`` is None.

    delay = time the hit is RAISED - time of the true start, floored at 0. A missed event has delay
    ``inf``; it is never dropped.

    ``confirm_rows``: an alarm that must persist for ``min_duration`` rows before it counts cannot be
    announced at its first row. It is raised ``confirm_rows = min_duration - 1`` rows after it
    starts (clipped to the last row), and that is when the operator learns of it. Matching still
    uses the alarm's start; only the delay uses the raise time.
    """
    if confirm_rows < 0:
        raise ValueError("confirm_rows must be >= 0")
    m = match_events(true_events, pred_events, early_tolerance)
    clock = None if times is None else _seconds(times)
    delays = np.full(len(true_events), np.inf)
    for k, ((ts, _te), ps) in enumerate(zip(true_events, m["first_detection"])):
        if ps is not None:
            raised = ps + confirm_rows
            if clock is not None:
                raised = min(raised, len(clock) - 1)
            raw = (raised - ts) if clock is None else (clock[raised] - clock[ts])
            delays[k] = max(0.0, float(raw))
    return delays


def delay_summary(delays) -> dict:
    """Median and 90th percentile over ALL events, missed ones counted as ``inf``.

    Quantiles use the "higher" rule (no interpolation), so the answer is always an observed delay
    or ``inf``: if half or more of the events are missed, the median delay is ``inf``.
    """
    d = np.asarray(delays, dtype=float)
    if d.size == 0:
        return {"n_events": 0, "n_detected": 0, "median": float("nan"), "p90": float("nan")}
    return {
        "n_events": int(d.size), "n_detected": int(np.isfinite(d).sum()),
        "median": float(np.quantile(d, 0.5, method="higher")),
        "p90": float(np.quantile(d, 0.9, method="higher")),
    }


def normal_hours(true_events, times, max_gap: float | None = None) -> float:
    """Hours of normal operation covered by the sequence.

    Row ``i`` stands for the interval from ``times[i]`` to ``times[i+1]``; the interval counts as
    normal when row ``i`` is outside every true event. The last row has no following interval.
    ``max_gap`` (seconds): an interval longer than this is treated as unmonitored and contributes
    only ``max_gap``. ``None`` counts wall-clock time in full.
    """
    clock = _seconds(times)
    if len(clock) < 2:
        return 0.0
    dt = np.diff(clock)
    if (dt < 0).any():
        raise ValueError("times must be non-decreasing")
    if max_gap is not None:
        dt = np.minimum(dt, max_gap)
    normal = np.ones(len(clock), dtype=bool)
    for s, e in true_events:
        normal[s:e] = False
    return float(dt[normal[:-1]].sum() / 3600.0)


def false_alarms_per_hour(true_events, pred_events, times, early_tolerance: int = 0,
                          max_gap: float | None = None) -> float:
    """False alarms divided by hours of normal operation. NaN when there is no normal time."""
    hours = normal_hours(true_events, times, max_gap)
    if hours <= 0:
        return float("nan")
    labels = match_events(true_events, pred_events, early_tolerance)["pred_label"]
    return labels.count("false_alarm") / hours


# --------------------------------------------------------------------------- many experiments
def evaluate_experiments(tidy: pd.DataFrame, flagged, *, burn_in: int = 0, min_duration: int = 1,
                         merge_gap: int = 0, early_tolerance: int = 0, max_gap: float | None = None) -> dict:
    """Pool event-level results over every experiment in ``tidy``.

    ``flagged`` is a 0/1 value per row of ``tidy``. Rows with ``t < burn_in`` are removed from each
    experiment before anything is computed (they were used for calibration). Delays include the
    ``min_duration - 1`` confirmation rows. Counts and hours are
    summed over experiments and the ratios are taken once, at the end: with one event per experiment,
    per-experiment recall is 0 or 1 and averaging per-experiment rates would weight short recordings
    as much as long ones.
    """
    flagged = np.asarray(flagged).astype(int).ravel()
    if len(flagged) != len(tidy):
        raise ValueError("flagged must have one value per row of tidy")
    frame = tidy[["experiment_id", "t", "datetime", "anomaly"]].assign(_flag=flagged)
    n_hits = n_false = n_redundant = 0
    hours = 0.0
    delays: list[float] = []
    for _, g in frame.groupby("experiment_id", sort=False):
        g = g.sort_values("t", kind="stable")
        g = g[g["t"] >= burn_in]
        if g.empty:
            continue
        true_events = extract_events(g["anomaly"].to_numpy())
        alarms = extract_events(g["_flag"].to_numpy(), min_duration=min_duration, merge_gap=merge_gap)
        times = g["datetime"].to_numpy()
        labels = match_events(true_events, alarms, early_tolerance)["pred_label"]
        n_hits += labels.count("hit")
        n_false += labels.count("false_alarm")
        n_redundant += labels.count("redundant")
        hours += normal_hours(true_events, times, max_gap)
        delays += detection_delay(true_events, alarms, times, early_tolerance,
                                  confirm_rows=min_duration - 1).tolist()
    summary = delay_summary(delays)
    n_events = summary["n_events"]
    return {
        "n_events": n_events, "n_detected": summary["n_detected"],
        "event_recall": summary["n_detected"] / n_events if n_events else float("nan"),
        "n_alarms": n_hits + n_false + n_redundant, "n_hits": n_hits,
        "n_false_alarms": n_false, "n_redundant": n_redundant,
        "event_precision": n_hits / (n_hits + n_false) if n_hits + n_false else float("nan"),
        "normal_hours": hours,
        "false_alarms_per_hour": n_false / hours if hours > 0 else float("nan"),
        "delays_s": delays, "median_delay_s": summary["median"], "p90_delay_s": summary["p90"],
    }
