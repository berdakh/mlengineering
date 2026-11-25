"""Pure computation: a DataFrame in, a DataFrame out. No file paths, no printing."""
from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = ("room", "timestamp", "temp_c")


def summarize(readings: pd.DataFrame) -> pd.DataFrame:
    """Mean, range and count of valid readings per room, in first-seen room order."""
    missing = [c for c in REQUIRED_COLUMNS if c not in readings.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    valid = readings.dropna(subset=["temp_c"])
    summary = valid.groupby("room", sort=False)["temp_c"].agg(
        mean="mean", range=lambda s: s.max() - s.min(), n="count"
    )
    return summary.round({"mean": 2, "range": 2}).reset_index()
