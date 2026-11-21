"""Tiny SYNTHETIC files in the SKAB raw format, so tests need no download."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAW_SENSORS = [
    "Accelerometer1RMS",
    "Accelerometer2RMS",
    "Current",
    "Pressure",
    "Temperature",
    "Thermocouple",
    "Voltage",
    "Volume Flow RateRMS",
]


def write_experiment(
    path: Path, n_rows: int, start: str, labelled: bool = True, seed: int = 0, shuffle: bool = False
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {"datetime": pd.date_range(start, periods=n_rows, freq="s").strftime("%Y-%m-%d %H:%M:%S")}
    )
    for i, name in enumerate(RAW_SENSORS):
        df[name] = np.round(rng.normal(10.0 * (i + 1), 1.0, n_rows), 4)
    if labelled:
        anomaly = np.zeros(n_rows)
        anomaly[n_rows // 2 :] = 1.0
        df["anomaly"] = anomaly
        df["changepoint"] = 0.0
        df.loc[n_rows // 2, "changepoint"] = 1.0
    if shuffle:
        df = df.sample(frac=1.0, random_state=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False)
    return df


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    root = tmp_path / "skab"
    write_experiment(root / "valve1" / "0.csv", 20, "2020-03-09 10:00:00", seed=1)
    write_experiment(root / "valve1" / "2.csv", 22, "2020-03-09 11:00:00", seed=2, shuffle=True)
    write_experiment(root / "valve1" / "10.csv", 30, "2020-03-09 12:00:00", seed=3)
    write_experiment(root / "other" / "1.csv", 12, "2020-03-01 15:00:00", seed=4)
    write_experiment(
        root / "anomaly-free" / "anomaly-free.csv", 40, "2020-02-08 13:00:00", labelled=False, seed=5
    )
    (root / "MANIFEST.json").write_text("{}")
    return root
