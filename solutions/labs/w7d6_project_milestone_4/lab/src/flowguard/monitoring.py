"""Monitoring building blocks: input drift (PSI), alarm rate, events, delayed-label evaluation. GIVEN.

A minimal version of what w7d2 (drift with calibrated thresholds) and w7d3 (delayed labels) build in
full. Nothing here needs labels except ``delayed_label_report``.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

EPS = 1e-4


def psi(reference: np.ndarray, current: np.ndarray, edges: np.ndarray) -> float:
    """Population stability index of ``current`` against ``reference`` on fixed bin ``edges``.

    PSI = sum_b (q_b - p_b) * ln(q_b / p_b), with p (reference) and q (current) bin proportions,
    each floored at EPS so that empty bins do not give infinities.
    """
    p = np.histogram(reference, bins=edges)[0].astype(float)
    q = np.histogram(current, bins=edges)[0].astype(float)
    p = np.maximum(p / max(p.sum(), 1.0), EPS)
    q = np.maximum(q / max(q.sum(), 1.0), EPS)
    return float(np.sum((q - p) * np.log(q / p)))


@dataclass
class DriftMonitor:
    """PSI of a window of inputs against a reference sample, alerting above a calibrated threshold."""
    reference: np.ndarray
    edges: np.ndarray
    threshold: float

    @classmethod
    def calibrate(cls, reference: np.ndarray, windows: Sequence[np.ndarray], n_bins: int = 10,
                  quantile: float = 1.0) -> "DriftMonitor":
        """Bins from reference quantiles (outer edges open); threshold = ``quantile`` of the PSI of
        ``windows`` that are known to be normal (e.g. each development experiment's normal rows)."""
        inner = np.quantile(reference, np.linspace(0, 1, n_bins + 1)[1:-1])
        edges = np.concatenate([[-np.inf], np.unique(inner), [np.inf]])
        values = [psi(reference, w, edges) for w in windows if len(w)]
        return cls(reference=np.asarray(reference, dtype=float), edges=edges,
                   threshold=float(np.quantile(values, quantile)))

    def check(self, window: np.ndarray) -> tuple[float, bool]:
        value = psi(self.reference, np.asarray(window, dtype=float), self.edges)
        return value, value > self.threshold


def alarm_rate_alert(alarms: int, values: int, budget: float) -> tuple[float, bool]:
    """Fraction of scored values that raised an alarm, and whether it exceeds ``budget``."""
    rate = alarms / values if values else 0.0
    return rate, rate > budget


def extract_events(flags: Sequence[bool], min_duration: int, merge_gap: int) -> list[tuple[int, int]]:
    """Runs of True as (start, end exclusive) after merging gaps <= merge_gap; keep len >= min_duration."""
    runs, start = [], None
    for i, f in enumerate(list(flags) + [False]):
        if f and start is None:
            start = i
        elif not f and start is not None:
            runs.append([start, i])
            start = None
    merged: list[list[int]] = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= merge_gap:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    return [(a, b) for a, b in merged if b - a >= min_duration]


def delayed_label_report(replays: Sequence[dict]) -> dict:
    """Event-level evaluation once labels arrive. Each replay: {"events": [(a, b), ...], "labels": [0/1, ...]}.

    Returns faults (labelled anomalous segments), detected faults, false alarm events, and recall. Only
    replays whose labels have arrived are passed in: the estimate covers labelled traffic only.
    """
    faults = detected = false_events = 0
    for r in replays:
        y = np.asarray(r["labels"], dtype=int)
        segs = extract_events(y.astype(bool), 1, 0)
        faults += len(segs)
        for a, b in segs:
            if any(ea < b and eb > a for ea, eb in r["events"]):
                detected += 1
        false_events += sum(1 for ea, eb in r["events"] if not y[ea:eb].any())
    return {"labelled_replays": len(replays), "faults": faults, "faults_detected": detected,
            "false_alarm_events": false_events, "event_recall": detected / faults if faults else None}
