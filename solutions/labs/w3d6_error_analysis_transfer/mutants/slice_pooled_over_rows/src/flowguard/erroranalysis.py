"""Error analysis for point-level detector output: where, how and for which experiments it fails.

Conventions (the checks rely on them):
* a row is flagged when ``score >= threshold``;
* ``scores`` and ``labels`` are aligned with the rows of ``tidy``; rows with ``t < burn_in`` are ignored;
* the experiment is the unit of analysis. Slice values are means over experiments, never row-pooled;
* a quantity that cannot be computed is ``NaN``, never 0.0. "No positives, so recall is undefined"
  and "recall is zero" are different findings;
* positions are row indices ``t`` within the experiment (time gaps in the recording are not expanded).
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

MIN_EXPERIMENTS_FOR_INTERVAL = 5
ERROR_KINDS = ("miss", "late", "boundary", "fragment", "pre_onset", "post_event", "false_alarm")


def _aligned(scores, labels, threshold: float, tidy: pd.DataFrame, burn_in: int) -> pd.DataFrame:
    scores = np.asarray(scores, dtype=float).ravel()
    labels = np.asarray(labels).astype(int).ravel()
    if not (len(scores) == len(labels) == len(tidy)):
        raise ValueError("scores, labels and tidy must have the same number of rows")
    if not np.isfinite(scores).all():
        raise ValueError("scores must be finite")
    frame = tidy[["experiment_id", "family", "t"]].reset_index(drop=True).copy()
    frame["label"] = labels
    frame["flag"] = (scores >= threshold).astype(int)
    return frame[frame["t"] >= burn_in]


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) positions of each run of True."""
    padded = np.r_[False, mask.astype(bool), False]
    change = np.flatnonzero(padded[1:] != padded[:-1])
    return [(int(a), int(b) - 1) for a, b in zip(change[::2], change[1::2])]


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator > 0 else float("nan")


def per_experiment_table(scores, labels, threshold: float, tidy: pd.DataFrame, burn_in: int = 0) -> pd.DataFrame:
    """One row per experiment: counts, precision, recall, false-alarm rate and detection delay.

    ``detection_delay`` is the number of rows between the first anomalous row and the first flagged
    anomalous row; NaN when the experiment has no anomaly or none of it was flagged.
    """
    rows = []
    for (experiment_id, family), g in _aligned(scores, labels, threshold, tidy, burn_in).groupby(
            ["experiment_id", "family"], sort=False):
        g = g.sort_values("t", kind="stable")
        y, f, t = g["label"].to_numpy(), g["flag"].to_numpy(), g["t"].to_numpy()
        tp, fp, fn = int((y & f).sum()), int(((1 - y) & f).sum()), int((y & (1 - f)).sum())
        onset = float(t[y == 1][0]) if y.any() else float("nan")
        hit = t[(y == 1) & (f == 1)]
        first = float(hit[0]) if len(hit) else float("nan")
        rows.append({
            "experiment_id": experiment_id, "family": family,
            "n_rows": int(len(g)), "n_pos": int(y.sum()), "n_flagged": int(f.sum()),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn),
            "false_alarm_rate": _ratio(fp, len(g) - int(y.sum())),
            "onset_t": onset, "first_detection_t": first, "detection_delay": first - onset,
        })
    return pd.DataFrame(rows)


def slice_metrics(df: pd.DataFrame, by: str, metric: str, levels: Iterable | None = None,
                  n_boot: int = 2000, seed: int = 0) -> pd.DataFrame:
    """Summarise a per-experiment ``metric`` column within each level of the ``by`` column.

    ``df`` has one row per experiment (for example the output of ``per_experiment_table`` with extra
    slicing columns). ``value`` is the mean over the experiments where the metric is defined.
    ``n_experiments`` and ``n_defined`` are always reported; a slice with ``n_defined == 0`` has
    ``value = NaN``. Levels listed in ``levels`` but absent from the data are reported with zero
    experiments instead of being dropped. A percentile bootstrap interval over experiments is given
    only when ``n_defined >= MIN_EXPERIMENTS_FOR_INTERVAL``; below that, read ``min`` and ``max``.
    """
    if by not in df.columns or metric not in df.columns:
        raise KeyError(f"columns {by!r} and {metric!r} must both be in df")
    rng = np.random.default_rng(seed)
    present = list(pd.unique(df[by].dropna()))
    wanted = list(levels) if levels is not None else present
    wanted += [level for level in present if level not in wanted]
    rows = []
    for level in wanted:
        part = df[df[by] == level]
        values = part[metric].to_numpy(dtype=float)
        defined = values[~np.isnan(values)]
        row = {
            "slice": level, "n_experiments": int(len(part)), "n_defined": int(len(defined)),
            "n_rows": int(part["n_rows"].sum()) if "n_rows" in part.columns else int(len(part)),
            "value": (float(np.average(defined, weights=part["n_rows"].to_numpy(dtype=float)[~np.isnan(values)]))
                      if len(defined) and "n_rows" in part.columns else
                      float(defined.mean()) if len(defined) else float("nan")),
            "min": float(defined.min()) if len(defined) else float("nan"),
            "max": float(defined.max()) if len(defined) else float("nan"),
            "ci_low": float("nan"), "ci_high": float("nan"),
        }
        if len(defined) >= MIN_EXPERIMENTS_FOR_INTERVAL:
            means = defined[rng.integers(0, len(defined), size=(n_boot, len(defined)))].mean(axis=1)
            row["ci_low"], row["ci_high"] = (float(q) for q in np.quantile(means, [0.025, 0.975]))
        rows.append(row)
    return pd.DataFrame(rows, columns=["slice", "n_experiments", "n_defined", "n_rows", "value",
                                       "min", "max", "ci_low", "ci_high"])


def error_segments(scores, labels, threshold: float, tidy: pd.DataFrame, late_after: int = 30,
                   burn_in: int = 0) -> pd.DataFrame:
    """One row per contiguous run of wrong rows, classified by what kind of failure it is.

    Missed-row runs (label 1, not flagged), relative to the anomalous event they belong to:
      ``miss``      no row of the event was flagged; the run is the whole event
      ``late``      the event was detected, but only after more than ``late_after`` rows
      ``boundary``  the event was detected within ``late_after`` rows of its onset
      ``fragment``  rows lost after the first detection (the alarm dropped out or cleared early)
    False-alarm runs (label 0, flagged):
      ``boundary``     at most ``late_after`` rows long and touching the start or end of an event
      ``pre_onset``    before the experiment's first event
      ``post_event``   after the experiment's last event
      ``false_alarm``  in an experiment with no event, or between two events
    """
    out = []
    for (experiment_id, family), g in _aligned(scores, labels, threshold, tidy, burn_in).groupby(
            ["experiment_id", "family"], sort=False):
        g = g.sort_values("t", kind="stable")
        y, f, t = g["label"].to_numpy(), g["flag"].to_numpy(), g["t"].to_numpy()
        events = _runs(y == 1)

        def add(kind: str, a: int, b: int) -> None:
            out.append({"experiment_id": experiment_id, "family": family, "kind": kind,
                        "start_t": int(t[a]), "end_t": int(t[b]), "n_rows": b - a + 1})

        for start, end in events:
            hits = np.flatnonzero(f[start:end + 1])
            if len(hits) == 0:
                add("miss", start, end)
                continue
            first_hit = start + int(hits[0])
            for a, b in _runs((f[start:end + 1] == 0)):
                a, b = a + start, b + start
                if a == start:
                    add("late" if (first_hit - start) > late_after else "boundary", a, b)
                else:
                    add("fragment", a, b)
        for a, b in _runs((y == 0) & (f == 1)):
            touches = any(b + 1 == start or a - 1 == end for start, end in events)
            if not events:
                kind = "false_alarm"
            elif touches and (b - a + 1) <= late_after:
                kind = "boundary"
            elif b < events[0][0]:
                kind = "pre_onset"
            elif a > events[-1][1]:
                kind = "post_event"
            else:
                kind = "false_alarm"
            add(kind, a, b)
    return pd.DataFrame(out, columns=["experiment_id", "family", "kind", "start_t", "end_t", "n_rows"])


def summarise_segments(segments: pd.DataFrame) -> pd.DataFrame:
    """Frequency table of failure kinds: segments, rows and experiments affected."""
    if segments.empty:
        return pd.DataFrame(columns=["kind", "n_segments", "n_rows", "n_experiments"])
    grouped = segments.groupby("kind", sort=False)
    table = pd.DataFrame({
        "n_segments": grouped.size(), "n_rows": grouped["n_rows"].sum(),
        "n_experiments": grouped["experiment_id"].nunique(),
    }).reset_index()
    return table.sort_values("n_rows", ascending=False, kind="stable").reset_index(drop=True)
