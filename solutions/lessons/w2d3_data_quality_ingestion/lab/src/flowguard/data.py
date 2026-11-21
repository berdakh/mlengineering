"""Reading raw SKAB files into the canonical tidy schema (docs/FLOWGUARD_SPEC.md).

Reading is deliberately *faithful*: rows keep their file order and nothing is
dropped, sorted or repaired. Whether the order is right is a question for
``flowguard.quality``; a loader that silently sorts would hide the answer.
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
FAMILIES = ("anomaly-free", "other", "valve1", "valve2")
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def load_experiment(path: str | Path) -> pd.DataFrame:
    """Read one raw file. Every parsing decision is explicit.

    * separator ``;``, decimal point ``.``, no index column
    * ``datetime`` parsed with a fixed format (timezone-naive, as recorded)
    * sensors forced to float64; unparseable cells become NaN for the quality checks to find
    * labels are int when every value is 0/1 (absent labels, as in ``anomaly-free``, become 0);
      otherwise they stay float so the quality check can report the offending values

    Raises ValueError naming the file and the columns if a required column is absent.
    """
    path = Path(path)
    raw = pd.read_csv(path, sep=";", decimal=".", dtype=str, keep_default_na=False)
    optional = set(LABEL_COLUMNS)
    missing = [c for c in RAW_TO_CANONICAL if c not in raw.columns and RAW_TO_CANONICAL[c] not in optional]
    if missing:
        raise ValueError(f"{path}: missing required column(s) {missing}")
    df = raw.rename(columns=RAW_TO_CANONICAL)
    out = pd.DataFrame(index=df.index)
    out["datetime"] = pd.to_datetime(df["datetime"], format=DATETIME_FORMAT, errors="coerce")
    for col in SENSOR_COLUMNS:
        out[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")
    for col in LABEL_COLUMNS:
        values = pd.to_numeric(df[col], errors="coerce") if col in df.columns else pd.Series(0, index=df.index)
        out[col] = values.astype("int64") if values.isin([0, 1]).all() else values.astype("float64")
    return out


def load_raw(raw_dir: str | Path) -> pd.DataFrame:
    """All experiments under ``raw_dir/<family>/<n>.csv`` as one tidy table.

    Experiments are concatenated in sorted ``experiment_id`` order; rows inside an
    experiment keep their file order and ``t`` is the 0-based row index in the file.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        raise FileNotFoundError(f"raw directory not found: {raw_dir}")
    paths = sorted(p for p in raw_dir.glob("*/*.csv"))
    if not paths:
        raise FileNotFoundError(f"no <family>/<n>.csv files under {raw_dir}")
    frames = []
    for path in sorted(paths, key=lambda p: f"{p.parent.name}/{p.stem}"):
        df = load_experiment(path)
        df.insert(0, "t", range(len(df)))
        df.insert(0, "family", path.parent.name)
        df.insert(0, "experiment_id", f"{path.parent.name}/{path.stem}")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)[list(TIDY_COLUMNS)]
