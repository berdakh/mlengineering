"""Deliberately slow, obviously-correct reference for the feature contract (row-by-row loops)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def slow_features(tidy: pd.DataFrame, windows, columns, max_gap_s: float) -> pd.DataFrame:
    out = {}
    for c in columns:
        for w in windows:
            for stat in ("mean", "std", "min", "max", "slope", "ewma"):
                out[f"{c}__{stat}_{w}"] = np.full(len(tidy), np.nan)
        out[f"{c}__diff1"] = np.full(len(tidy), np.nan)
    positions = {eid: np.flatnonzero((tidy["experiment_id"] == eid).to_numpy())
                 for eid in tidy["experiment_id"].unique()}
    for rows in positions.values():
        times = tidy["datetime"].to_numpy()[rows]
        rows = rows[np.argsort(times, kind="stable")]
        times = tidy["datetime"].to_numpy()[rows]
        start = 0  # index (within this experiment) where the current segment began
        for i in range(len(rows)):
            if i > 0 and (times[i] - times[i - 1]) / np.timedelta64(1, "s") > max_gap_s:
                start = i
            for c in columns:
                x = tidy[c].to_numpy(dtype=float)[rows]
                if i > start:
                    out[f"{c}__diff1"][rows[i]] = x[i] - x[i - 1]
                for w in windows:
                    alpha = 2.0 / (w + 1.0)
                    ewma = x[start]
                    for j in range(start + 1, i + 1):
                        ewma = alpha * x[j] + (1 - alpha) * ewma
                    out[f"{c}__ewma_{w}"][rows[i]] = ewma
                    if i - start + 1 >= w:
                        win = x[i - w + 1:i + 1]
                        out[f"{c}__mean_{w}"][rows[i]] = win.mean()
                        out[f"{c}__std_{w}"][rows[i]] = win.std(ddof=1)
                        out[f"{c}__min_{w}"][rows[i]] = win.min()
                        out[f"{c}__max_{w}"][rows[i]] = win.max()
                        out[f"{c}__slope_{w}"][rows[i]] = np.polyfit(np.arange(w), win, 1)[0]
    return pd.DataFrame(out)
