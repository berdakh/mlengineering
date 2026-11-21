"""Reference solution: causal time-based window features for irregularly sampled series."""
from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


def time_window_features(
    df: pd.DataFrame, windows_s: Sequence[float] = (30.0, 120.0), max_gap_s: float = 20.0
) -> pd.DataFrame:
    """Features over (tau - w, tau] per series and continuous segment; see challenge/README.md."""
    for column in ("series_id", "timestamp", "value"):
        if column not in df.columns:
            raise ValueError(f"missing column: {column}")
    out = pd.DataFrame({"series_id": df["series_id"], "timestamp": df["timestamp"]}, index=df.index)
    out["dt_prev_s"] = np.nan
    out["segment"] = 0
    for w in windows_s:
        for stat in ("mean", "std", "count"):
            out[f"{stat}_{int(w)}s"] = np.nan
    for _, group in df.groupby("series_id", sort=False):
        group = group.sort_values("timestamp", kind="stable")
        dt = group["timestamp"].diff().dt.total_seconds()
        segment = (dt > max_gap_s).cumsum()
        out.loc[group.index, "dt_prev_s"] = dt
        out.loc[group.index, "segment"] = segment
        for _, seg in group.groupby(segment):
            series = pd.Series(seg["value"].to_numpy(dtype=float), index=pd.DatetimeIndex(seg["timestamp"]))
            age_s = (seg["timestamp"] - seg["timestamp"].iloc[0]).dt.total_seconds().to_numpy()
            for w in windows_s:
                roll = series.rolling(max(2, int(round(w / 4.75))), min_periods=1)
                full = age_s >= w
                out.loc[seg.index, f"count_{int(w)}s"] = roll.count().to_numpy()
                out.loc[seg.index, f"mean_{int(w)}s"] = np.where(full, roll.mean().to_numpy(), np.nan)
                out.loc[seg.index, f"std_{int(w)}s"] = np.where(full, roll.std().to_numpy(), np.nan)
    return out
