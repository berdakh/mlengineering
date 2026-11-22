"""Worked example: the same detectors ranked by point-level and by event-level metrics.

    python lessons/w3d4_point_vs_event_evaluation/example/toy_point_vs_event.py

SYNTHETIC data: one 6-hour recording sampled every 2 s, with one long event (40 min) and nine short
ones (1 min each). The five "detectors" are constructed by hand from the labels so that their
behaviour is known exactly. Nothing here says anything about a real detector; the point is how the
two families of metrics order them.

The event code below is a deliberately small pandas version (runs via ``cumsum``, any-overlap
matching). The lab builds the stricter, start-based rules in NumPy with post-processing and edge cases.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DT_S = 2.0                      # sampling interval in seconds
N = int(6 * 3600 / DT_S)        # 6 hours


def runs(flags: np.ndarray) -> pd.DataFrame:
    """Runs of ones as a table with columns start, end (end exclusive)."""
    s = pd.Series(flags.astype(int))
    run_id = (s != s.shift()).cumsum()                      # a new id every time the value changes
    table = s.groupby(run_id).agg(value="first", start=lambda x: x.index[0], end=lambda x: x.index[-1] + 1)
    return table[table["value"] == 1][["start", "end"]].reset_index(drop=True)


def make_labels() -> np.ndarray:
    y = np.zeros(N, dtype=int)
    y[1000:2200] = 1                                        # 1200 rows = 40 minutes
    for k in range(9):                                      # nine events of 30 rows = 1 minute
        start = 3000 + 800 * k
        y[start:start + 30] = 1
    return y


def detectors(y: np.ndarray) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(0)
    events = runs(y)
    out = {}

    late = np.zeros(N, dtype=int)                           # fires on the last 80 % of every event
    for s, e in events.itertuples(index=False):
        late[s + int(0.2 * (e - s)):e] = 1
    out["late (last 80 % of each event)"] = late

    onset = np.zeros(N, dtype=int)                          # 5 rows at each onset, then silence
    for s, e in events.itertuples(index=False):
        onset[s:s + 5] = 1
    out["onset only (first 5 rows)"] = onset

    long_only = np.zeros(N, dtype=int)                      # finds the 40-minute event, nothing else
    long_only[1000:2200] = 1
    out["long event only"] = long_only

    chatter = (y == 1) & (rng.random(N) < 0.5)              # half the event rows, at random
    out["chattering (50 % of event rows)"] = chatter.astype(int)

    noisy = onset.copy()                                    # onset detector + 20 isolated false flags
    noisy[rng.choice(np.flatnonzero(y == 0), size=20, replace=False)] = 1
    out["onset only + 20 stray flags"] = noisy
    return out


def evaluate(y: np.ndarray, pred: np.ndarray) -> dict:
    tp = int(np.sum((pred == 1) & (y == 1)))
    precision = tp / pred.sum() if pred.sum() else 0.0
    recall = tp / y.sum()
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)

    true_events, alarms = runs(y), runs(pred)
    found, delays = 0, []
    for s, e in true_events.itertuples(index=False):
        overlapping = alarms[(alarms["start"] < e) & (alarms["end"] > s)]       # any overlap
        if len(overlapping):
            found += 1
            delays.append(max(0, overlapping["start"].min() - s) * DT_S)
    false_alarms = sum(
        not ((true_events["start"] < a_end) & (true_events["end"] > a_start)).any()
        for a_start, a_end in alarms.itertuples(index=False))
    normal_hours = (y == 0).sum() * DT_S / 3600
    return {
        "point P": round(precision, 3), "point R": round(recall, 3), "point F1": round(f1, 3),
        "events found": f"{found}/{len(true_events)}", "alarms": len(alarms),
        "false alarms/h": round(false_alarms / normal_hours, 2),
        "median delay s": float(np.median(delays)) if delays else float("nan"),
    }


def main() -> None:
    y = make_labels()
    print(f"rows {N}, sampling {DT_S:.0f} s, anomalous rows {y.sum()} "
          f"({y.mean():.1%}), events {len(runs(y))}; the long event holds "
          f"{1200 / y.sum():.0%} of the anomalous rows\n")
    table = pd.DataFrame({name: evaluate(y, pred) for name, pred in detectors(y).items()}).T
    print(table.to_string())


if __name__ == "__main__":
    main()
