"""SYNTHETIC raw directories in the SKAB file format, for the checks only.

Values are drawn around the real sensors' typical levels so that reasonable
plausibility limits pass, but they are simulated: nothing about SKAB itself can
be concluded from them. Each defect function plants exactly one problem in
experiment ``valve1/1`` and leaves the other experiments clean.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW_SENSORS = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure",
               "Temperature", "Thermocouple", "Voltage", "Volume Flow RateRMS"]
LEVELS = {"Accelerometer1RMS": (0.08, 0.004), "Accelerometer2RMS": (0.13, 0.006), "Current": (1.37, 0.05),
          "Pressure": (0.05, 0.02), "Temperature": (85.0, 0.4), "Thermocouple": (25.5, 0.1),
          "Voltage": (230.0, 2.0), "Volume Flow RateRMS": (74.0, 1.5)}
N_ROWS = 300
BAD = "valve1/1"
CLEAN_LABELLED = ("valve1/0", "other/1")
MANIFEST = {"source": "https://example.invalid/synthetic-skab", "commit": "abc123synthetic", "licence": "GPL-3.0"}


def experiment(seed: int, start: str, labelled: bool = True, n: int = N_ROWS) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({"datetime": pd.date_range(start, periods=n, freq="s").strftime("%Y-%m-%d %H:%M:%S")})
    for name, (mean, sd) in LEVELS.items():
        df[name] = np.round(mean + sd * rng.standard_normal(n), 6)
    if labelled:
        anomaly = np.zeros(n)
        anomaly[150:220] = 1.0
        df.loc[150:219, "Volume Flow RateRMS"] -= 8.0
        changepoint = np.zeros(n)
        changepoint[[150, 220]] = 1.0
        df["anomaly"], df["changepoint"] = anomaly, changepoint   # floats "0.0"/"1.0", as in the real files
    return df


def clean_frames() -> dict[str, pd.DataFrame]:
    return {
        "anomaly-free/anomaly-free": experiment(0, "2020-02-08 13:30:00", labelled=False),
        "other/1": experiment(1, "2020-03-01 15:00:00"),
        "valve1/0": experiment(2, "2020-03-09 10:14:33"),
        "valve1/1": experiment(3, "2020-03-09 12:00:00"),
    }


def write_raw(root: Path, frames: dict[str, pd.DataFrame], manifest: bool = True) -> Path:
    for exp, df in frames.items():
        path = root / f"{exp}.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, sep=";", index=False, lineterminator="\n")
    if manifest:
        (root / "MANIFEST.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    return root


# --- defects, each applied to valve1/1 ---------------------------------------------------
def duplicate_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Rows 40-44 are written twice with different sensor values (a logger retry)."""
    extra = df.iloc[40:45].copy()
    extra["Current"] += 0.01
    return pd.concat([df.iloc[:45], extra, df.iloc[45:]], ignore_index=True)


def unsorted_rows(df: pd.DataFrame) -> pd.DataFrame:
    """A block of 30 rows was appended out of time order."""
    return pd.concat([df.iloc[:60], df.iloc[90:], df.iloc[60:90]], ignore_index=True)


def gap_300s(df: pd.DataFrame) -> pd.DataFrame:
    """The logger stopped for 300 s after row 99; later timestamps are shifted."""
    out = df.copy()
    stamps = pd.to_datetime(out["datetime"])
    stamps[100:] = stamps[100:] + pd.Timedelta(seconds=299)
    out["datetime"] = stamps.dt.strftime("%Y-%m-%d %H:%M:%S")
    return out


def stuck_sensor(df: pd.DataFrame) -> pd.DataFrame:
    """Voltage reports one value for the last 200 rows."""
    out = df.copy()
    out.loc[100:, "Voltage"] = 230.0
    return out


def non_binary_label(df: pd.DataFrame) -> pd.DataFrame:
    """Three samples carry the label 2.0."""
    out = df.copy()
    out.loc[160:162, "anomaly"] = 2.0
    return out


def missing_column(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop(columns=["Pressure"])


DEFECTS = {
    "duplicate_timestamps": (duplicate_timestamps, "error"),
    "unsorted_rows": (unsorted_rows, "error"),
    "non_binary_label": (non_binary_label, "error"),
    "gap_300s": (gap_300s, "warning"),
    "stuck_sensor": (stuck_sensor, "warning"),
}


def frames_with(defect: str) -> dict[str, pd.DataFrame]:
    frames = clean_frames()
    fn = DEFECTS[defect][0] if defect in DEFECTS else globals()[defect]
    frames[BAD] = fn(frames[BAD])
    return frames
