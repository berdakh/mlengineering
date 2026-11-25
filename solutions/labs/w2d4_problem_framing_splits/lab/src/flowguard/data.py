"""Loading SKAB experiment files into the canonical tidy table (snapshot per docs/maintainers/flowguard-spec.md)."""
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
    """One raw SKAB file -> tidy rows for one experiment, sorted by time."""
    path = Path(path)
    df = pd.read_csv(path, sep=";", parse_dates=["datetime"]).rename(columns=_RENAME)
    missing = [c for c in SENSOR_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing sensor columns: {missing}")
    for label in ("anomaly", "changepoint"):      # absent in the anomaly-free recording
        df[label] = df[label].astype(int) if label in df.columns else 0
    df = df.sort_values("datetime", kind="stable").reset_index(drop=True)
    df.insert(0, "t", range(len(df)))
    df.insert(0, "family", path.parent.name)
    df.insert(0, "experiment_id", f"{path.parent.name}/{path.stem}")
    return df[list(TIDY_COLUMNS)]


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """All experiments under ``raw_dir/<family>/<n>.csv`` as one tidy table."""
    raw_dir = Path(raw_dir)
    files = sorted(raw_dir.glob("*/*.csv"))
    if not files:
        raise FileNotFoundError(
            f"no SKAB files under {raw_dir}. Run `python project/get_skab.py` from the repository root first."
        )
    tidy = pd.concat([load_experiment(f) for f in files], ignore_index=True)
    return tidy.sort_values(["experiment_id", "datetime"], kind="stable").reset_index(drop=True)
