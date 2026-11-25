"""Loading SKAB files into the tidy table. SNAPSHOT of the w1d6/w2d3 module (docs/maintainers/flowguard-spec.md).

Given to you in this lab; you do not need to edit it.
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
FAMILIES = ("anomaly-free", "valve1", "valve2", "other")


def load_experiment(path: str | Path) -> pd.DataFrame:
    """One SKAB CSV -> canonical columns, sorted by time. Labels are 0 when the file has none."""
    df = pd.read_csv(path, sep=";", parse_dates=["datetime"]).rename(columns=_RENAME)
    missing = [c for c in SENSOR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing sensor columns {missing}")
    for label in ("anomaly", "changepoint"):
        df[label] = df[label].astype(int) if label in df.columns else 0
    df = df.sort_values("datetime", kind="stable").reset_index(drop=True)
    return df[["datetime", *SENSOR_COLUMNS, "anomaly", "changepoint"]]


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """All experiments under ``raw_dir`` as one tidy table (see the spec for the schema)."""
    raw_dir = Path(raw_dir)
    frames = []
    for family in FAMILIES:
        files = sorted((raw_dir / family).glob("*.csv"), key=lambda p: (len(p.stem), p.stem))
        for path in files:
            df = load_experiment(path)
            df.insert(0, "t", range(len(df)))
            df.insert(0, "family", family)
            df.insert(0, "experiment_id", f"{family}/{path.stem}")
            frames.append(df)
    if not frames:
        raise FileNotFoundError(
            f"no SKAB files under {raw_dir}. Run `python project/get_skab.py` from the repository root first."
        )
    return pd.concat(frames, ignore_index=True)
