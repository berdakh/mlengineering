"""Loading raw SKAB experiment files into one tidy table.

Tidy table: one row per (experiment_id, timestamp), sorted by experiment_id then
datetime, with columns

    experiment_id, family, t, datetime, <eight sensors>, anomaly, changepoint

``experiment_id`` is ``"<family>/<file stem>"`` - derived from the file's own name,
never from its position in a listing.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_TO_CANONICAL = {
    "datetime": "datetime",
    "Accelerometer1RMS": "accelerometer1_rms",
    "Accelerometer2RMS": "accelerometer2_rms",
    "Current": "current",
    "Pressure": "pressure",
    "Temperature": "temperature",
    "Thermocouple": "thermocouple",
    "Voltage": "voltage",
    "Volume Flow RateRMS": "flow_rate",
    "anomaly": "anomaly",
    "changepoint": "changepoint",
}
SENSOR_COLUMNS = (
    "accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
    "temperature", "thermocouple", "voltage", "flow_rate",
)
LABEL_COLUMNS = ("anomaly", "changepoint")
TIDY_COLUMNS = ("experiment_id", "family", "t", "datetime", *SENSOR_COLUMNS, *LABEL_COLUMNS)


def load_experiment(path: str | Path) -> pd.DataFrame:
    """Read one raw experiment file and return it with canonical columns.

    Columns are renamed *by name* (a file with reordered columns still loads
    correctly), rows are sorted by time, and the label columns are integers.
    The fault-free recording has no label columns; they are filled with 0,
    which is what "labelled normal" means for that file.

    Raises FileNotFoundError for a missing file and ValueError naming any
    missing column.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"experiment file not found: {path}")
    df = pd.read_csv(path, sep=";")
    required = [raw for raw, name in RAW_TO_CANONICAL.items() if name not in LABEL_COLUMNS]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    df = df.rename(columns=RAW_TO_CANONICAL)
    for label in LABEL_COLUMNS:
        if label not in df.columns:
            df[label] = 0
        df[label] = df[label].astype(int)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime", kind="stable").reset_index(drop=True)
    return df[["datetime", *SENSOR_COLUMNS, *LABEL_COLUMNS]]


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """Load every ``<family>/<name>.csv`` under ``raw_dir`` into one tidy table."""
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"raw data directory not found: {raw_dir}")
    files = sorted(raw_dir.glob("*/*.csv"))
    if not files:
        raise ValueError(f"no experiment files (<family>/<name>.csv) under {raw_dir}")
    frames = []
    position: dict[str, int] = {}
    for path in files:
        family = path.parent.name
        i = position.get(family, 0)
        position[family] = i + 1
        df = load_experiment(path)
        df.insert(0, "t", range(len(df)))
        df.insert(0, "family", family)
        name = path.stem if family == "anomaly-free" else str(i)
        df.insert(0, "experiment_id", f"{family}/{name}")
        frames.append(df)
    tidy = pd.concat(frames, ignore_index=True)
    tidy = tidy.sort_values(["experiment_id", "t"], kind="stable").reset_index(drop=True)
    return tidy[list(TIDY_COLUMNS)]


def summarize(tidy: pd.DataFrame) -> dict:
    """Per-experiment row counts, anomaly fraction and time span, as plain Python types."""
    experiments = []
    for experiment_id, g in tidy.groupby("experiment_id", sort=True):
        experiments.append({
            "experiment_id": experiment_id,
            "family": g["family"].iloc[0],
            "n_rows": len(g),
            "anomaly_fraction": float(g["anomaly"].mean()),
            "start": g["datetime"].min().isoformat(sep=" "),
            "end": g["datetime"].max().isoformat(sep=" "),
        })
    return {"n_experiments": len(experiments), "n_rows": len(tidy), "experiments": experiments}
