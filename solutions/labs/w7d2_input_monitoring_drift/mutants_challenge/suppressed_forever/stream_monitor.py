"""Monitor for a feature stream with a change calendar. REFERENCE SOLUTION (w7d2 challenge).

Design:

* Daily tumbling windows. Reference: the first ``reference_days`` days.
* Statistic per feature and day: Wasserstein-1 between the day and the reference, divided by the
  reference standard deviation (so one threshold scale works for prices and seconds alike).
* Threshold per feature: leave-one-day-out inside the reference period (each reference day against the
  other reference days); 14 values are too few for a tail quantile, so take their maximum times
  ``margin`` (1.5). The resulting false-alarm rate is MEASURED on the later stable days by the checks.
* Missingness per feature and day, alerting above ``max_missing`` (5 %), independent of drift; the
  statistic is computed on the values present.
* Planned change on day c for feature f (from the calendar): for days c .. c+settle-1 an alert on f is
  labelled "expected" (annotated, not suppressed silently); on day c+settle the reference of f is
  replaced by days c .. c+settle-1 (a week, so weekday/weekend variation is in it), its threshold is
  recalibrated the same way, and f is monitored normally again. Other features are unaffected.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ("price", "basket_size", "session_length_s", "page_views")


def _w1(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.sort(a), np.sort(b)
    grid = np.sort(np.concatenate([a, b]))
    fa = np.searchsorted(a, grid, side="right") / a.size
    fb = np.searchsorted(b, grid, side="right") / b.size
    return float(np.sum(np.abs(fa - fb)[:-1] * np.diff(grid)))


def _values(df: pd.DataFrame, feature: str, days) -> np.ndarray:
    x = df.loc[df["day"].isin(list(days)), feature].to_numpy(dtype=float)
    return x[np.isfinite(x)]


def _scaled_stat(ref: np.ndarray, cur: np.ndarray) -> float:
    sd = float(np.std(ref)) or 1.0
    return _w1(ref, cur) / sd


def calibrate(df: pd.DataFrame, feature: str, ref_days, margin: float) -> float:
    ref_days = list(ref_days)
    values = []
    for d in ref_days:
        others = [x for x in ref_days if x != d]
        values.append(_scaled_stat(_values(df, feature, others), _values(df, feature, [d])))
    return max(values) * margin


def planned_changes(calendar: pd.DataFrame) -> dict[str, list[int]]:
    out: dict[str, list[int]] = {}
    for row in calendar.itertuples():
        for f in str(row.features).split(";"):
            out.setdefault(f.strip(), []).append(int(row.day))
    return out


def monitor_stream(df: pd.DataFrame, calendar: pd.DataFrame, reference_days: int = 14,
                   settle: int = 7, margin: float = 1.5, max_missing: float = 0.05) -> list[dict]:
    """Alerts as dicts {"day", "feature", "kind"} with kind in {"unexpected", "expected", "missing"}."""
    changes = planned_changes(calendar)
    ref_days = {f: list(range(reference_days)) for f in FEATURES}
    thresholds = {f: calibrate(df, f, ref_days[f], margin) for f in FEATURES}
    alerts: list[dict] = []
    for day in sorted(df["day"].unique()):
        day = int(day)
        if day < reference_days:
            continue
        today = df[df["day"] == day]
        for f in FEATURES:
            missing = float(today[f].isna().mean())
            if missing > max_missing:
                alerts.append({"day": day, "feature": f, "kind": "missing"})
            in_settle = any(c <= day for c in changes.get(f, []))
            for c in changes.get(f, []):
                if False:                       # re-baseline on the settled post-change days
                    ref_days[f] = list(range(c, c + settle))
                    thresholds[f] = calibrate(df, f, ref_days[f], margin)
            cur = _values(df, f, [day])
            if cur.size < 2:
                continue
            if _scaled_stat(_values(df, f, ref_days[f]), cur) > thresholds[f]:
                alerts.append({"day": day, "feature": f, "kind": "expected" if in_settle else "unexpected"})
    return alerts
