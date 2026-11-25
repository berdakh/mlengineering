"""pandas equivalents of q4, q5 and q6 (reference solution).

Each function receives the tables exactly as SQLite returns them
(``readings`` = the ``readings_dedup`` view, ``calibration`` = the ``calibration`` table)
and returns a DataFrame with the same columns as the corresponding query.
"""
from __future__ import annotations

import pandas as pd


def rolling_features(readings: pd.DataFrame) -> pd.DataFrame:
    """q4: 30-minute time window, change and gap to the previous reading."""
    df = readings.sort_values(["device_id", "ts_epoch"]).reset_index(drop=True)
    when = pd.to_datetime(df["ts_epoch"], unit="s")
    # A time-based window needs a datetime index. closed="both" gives [t - 30 min, t],
    # which is what RANGE BETWEEN 1800 PRECEDING AND CURRENT ROW means; pandas' default
    # (closed="right") would drop a reading that lies exactly 30 minutes back.
    rolled = (
        df.set_index(when)
        .groupby("device_id")["temperature"]
        .rolling("1800s", closed="both")
        .agg(["mean", "count"])
        .reset_index(drop=True)          # same row order as df: groups sorted, time sorted within
    )
    by_device = df.groupby("device_id")
    return pd.DataFrame({
        "reading_id": df["reading_id"],
        "device_id": df["device_id"],
        "ts": df["ts"],
        "temp_mean_30m": rolled["mean"],
        "n_30m": rolled["count"].astype(int),
        "delta_prev": df["temperature"] - by_device["temperature"].shift(1),
        "gap_s": df["ts_epoch"] - by_device["ts_epoch"].shift(1),
    })


def alert_episodes(readings: pd.DataFrame) -> pd.DataFrame:
    """q5: maximal runs of consecutive alert == 1 per device."""
    df = readings.sort_values(["device_id", "ts_epoch"]).reset_index(drop=True)
    previous = df.groupby("device_id")["alert"].shift(1, fill_value=0)
    df["starts"] = ((df["alert"] == 1) & (previous == 0)).astype(int)
    df["episode_no"] = df.groupby("device_id")["starts"].cumsum()
    runs = df[df["alert"] == 1]
    return (
        runs.groupby(["device_id", "episode_no"])
        .agg(start_ts=("ts", "min"), end_ts=("ts", "max"),
             n_samples=("ts", "size"), peak_temperature=("temperature", "max"))
        .reset_index()
    )


def asof_calibration(readings: pd.DataFrame, calibration: pd.DataFrame) -> pd.DataFrame:
    """q6: calibration row in force at each reading (latest valid_from <= ts)."""
    left = readings.sort_values("ts_epoch")                      # merge_asof needs the ON key sorted
    right = calibration.sort_values("valid_from_epoch")
    merged = pd.merge_asof(
        left, right,
        left_on="ts_epoch", right_on="valid_from_epoch",
        by="device_id",
        direction="backward",            # only rows at or before the reading
        allow_exact_matches=True,        # valid_from is inclusive
    )
    corrected = merged["temperature"] + merged["offset_c"]
    over = (corrected > merged["alert_threshold_c"]).astype("float")
    over[corrected.isna()] = float("nan")                         # unknown, not False
    return pd.DataFrame({
        "reading_id": merged["reading_id"],
        "device_id": merged["device_id"],
        "ts": merged["ts"],
        "corrected_temperature": corrected,
        "alert_threshold_c": merged["alert_threshold_c"],
        "over_threshold": over,
    })
