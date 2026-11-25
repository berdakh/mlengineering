"""A tiny SYNTHETIC project in SKAB format, for the w4d6 and w5d6 checks (copied from w4d6). Nothing here resembles real data.

``write_project(root)`` creates ``root/data/raw/skab/<family>/<n>.csv`` (semicolon separated, the
SKAB columns) and ``root/splits/v2.json``. Experiments have 220 rows; labelled ones contain one
anomalous segment (rows 130-189) where flow rate drops and vibration rises.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["Accelerometer1RMS", "Accelerometer2RMS", "Current", "Pressure", "Temperature",
           "Thermocouple", "Voltage", "Volume Flow RateRMS"]
LAYOUT = {"anomaly-free": ["anomaly-free"], "valve1": ["0", "1", "2", "3", "4", "5"],
          "valve2": ["0", "1", "2"], "other": ["1", "2", "3", "4"]}
MANIFEST = {
    "version": "v2", "seed": 0, "unit": "experiment_id",
    "test": ["other/1", "valve1/0", "valve2/0"],
    "dev_folds": [["valve1/1", "other/2"], ["valve1/2", "valve2/1"], ["valve1/3", "other/3"],
                  ["valve1/4", "valve1/5", "valve2/2", "other/4"]],
    "reference_normal": ["anomaly-free/anomaly-free"],
    "overlap_groups": [], "protocol_b": {"holdout_family": "other"},
}
N_ROWS, START, END = 220, 130, 190


def _experiment(rng: np.random.Generator, labelled: bool, strength: float) -> pd.DataFrame:
    t = pd.date_range("2020-03-01 10:00:00", periods=N_ROWS, freq="s")
    base = np.array([0.03, 0.04, 1.3, 0.2, 70.0, 25.0, 230.0, 32.0])
    scale = np.array([0.002, 0.002, 0.05, 0.02, 0.3, 0.2, 2.0, 0.4])
    x = base + rng.normal(0, 1, size=(N_ROWS, 8)) * scale
    anomaly = np.zeros(N_ROWS, dtype=int)
    if labelled:
        anomaly[START:END] = 1
        x[START:END, 7] -= strength * 2.0
        x[START:END, 0] += strength * 0.006
    df = pd.DataFrame(np.round(x, 5), columns=COLUMNS)
    df.insert(0, "datetime", t.strftime("%Y-%m-%d %H:%M:%S"))
    if labelled:
        df["anomaly"] = anomaly.astype(float)
        cp = np.zeros(N_ROWS)
        cp[[START, END]] = 1
        df["changepoint"] = cp
    return df


def write_project(root: str | Path, seed: int = 7) -> Path:
    root = Path(root)
    rng = np.random.default_rng(seed)
    for family, names in LAYOUT.items():
        for k, name in enumerate(names):
            out = root / "data" / "raw" / "skab" / family / f"{name}.csv"
            out.parent.mkdir(parents=True, exist_ok=True)
            df = _experiment(rng, family != "anomaly-free", strength=1.0 + 0.4 * k)
            df.to_csv(out, sep=";", index=False, lineterminator="\n")
    (root / "splits").mkdir(parents=True, exist_ok=True)
    (root / "splits" / "v2.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    return root
