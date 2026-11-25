"""Loading SKAB recordings into the tidy table (snapshot written to docs/maintainers/flowguard-spec.md).

Your own project gets this module in w1d6 and the ingest step in w2d3; this copy exists so the
w2d5 lab runs on its own.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

SENSOR_COLUMNS = (
    "accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
    "temperature", "thermocouple", "voltage", "flow_rate",
)
_RENAME = {
    "Accelerometer1RMS": "accelerometer1_rms", "Accelerometer2RMS": "accelerometer2_rms",
    "Current": "current", "Pressure": "pressure", "Temperature": "temperature",
    "Thermocouple": "thermocouple", "Voltage": "voltage", "Volume Flow RateRMS": "flow_rate",
}
TIDY_COLUMNS = ("experiment_id", "family", "t", "datetime", *SENSOR_COLUMNS, "anomaly", "changepoint")


def load_experiment(path: str | Path) -> pd.DataFrame:
    """One raw SKAB file -> canonical columns, sorted by time. Labels are 0 if absent."""
    df = pd.read_csv(path, sep=";", parse_dates=["datetime"]).rename(columns=_RENAME)
    missing = [c for c in SENSOR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing sensor columns: {missing}")
    for label in ("anomaly", "changepoint"):
        df[label] = df[label].astype(int) if label in df.columns else 0
    df = df.sort_values("datetime", kind="stable").reset_index(drop=True)
    return df[["datetime", *SENSOR_COLUMNS, "anomaly", "changepoint"]]


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """All experiments under ``raw_dir/<family>/<n>.csv`` as one tidy table."""
    raw_dir = Path(raw_dir)
    frames = []
    for path in sorted(raw_dir.glob("*/*.csv")):
        df = load_experiment(path)
        df.insert(0, "t", range(len(df)))
        df.insert(0, "family", path.parent.name)
        df.insert(0, "experiment_id", f"{path.parent.name}/{path.stem}")
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"no experiment files under {raw_dir}; run `python project/get_skab.py`")
    tidy = pd.concat(frames, ignore_index=True)
    return tidy.sort_values(["experiment_id", "datetime"], kind="stable").reset_index(drop=True)


def read_tidy(path: str | Path) -> pd.DataFrame:
    """Read a tidy CSV written by the ingest step (``data/interim/skab.csv``)."""
    df = pd.read_csv(path, parse_dates=["datetime"])
    missing = [c for c in TIDY_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is not a tidy table; missing columns: {missing}")
    return df
