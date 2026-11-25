"""SYNTHETIC inputs for the w3d2 checks. They isolate mechanisms; they say nothing about SKAB."""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]


def tidy(experiments: dict[str, int], seed: int = 0) -> pd.DataFrame:
    """A tidy frame in the flowguard schema. ``experiments`` maps experiment_id -> number of rows."""
    rng = np.random.default_rng(seed)
    frames = []
    for experiment_id, n in experiments.items():
        df = pd.DataFrame(rng.standard_normal((n, len(SENSORS))), columns=SENSORS)
        df.insert(0, "datetime", pd.Timestamp("2020-03-09 10:00:00") + pd.to_timedelta(np.arange(n), unit="s"))
        df.insert(0, "t", np.arange(n))
        df.insert(0, "family", experiment_id.split("/")[0])
        df.insert(0, "experiment_id", experiment_id)
        df["anomaly"] = 0 if experiment_id.startswith("anomaly-free") else (np.arange(n) >= n // 2).astype(int)
        df["changepoint"] = 0
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


FAMILY_TIDY = {"valve1/0": 6, "valve1/1": 5, "valve1/2": 7, "valve2/0": 6, "valve2/1": 4,
               "other/0": 5, "other/1": 6, "other/2": 5, "anomaly-free/anomaly-free": 9}


def manifest() -> dict:
    return {
        "version": "v2", "seed": 0, "unit": "experiment_id",
        "test": ["other/9", "valve1/9"],
        "dev_folds": [["other/0", "other/1", "valve1/0"], ["valve1/1", "valve2/0"], ["other/2", "valve1/2", "valve2/1"]],
        "reference_normal": ["anomaly-free/anomaly-free"],
        "overlap_groups": [["other/0", "other/1"]],
        "protocol_b": {"holdout_family": "other"},
    }


def machines(n_machines: int, rows: int, seed: int):
    """Planted within-group effect: the label depends on one honest feature plus a machine-level
    offset; four 'fingerprint' features identify the machine and carry nothing transferable."""
    rng = np.random.default_rng(seed)
    groups = np.repeat(np.arange(n_machines), rows)
    offset = rng.normal(0, 1.5, n_machines)[groups]
    fingerprint = rng.normal(0, 1, (n_machines, 4))[groups] + 0.05 * rng.standard_normal((len(groups), 4))
    signal = rng.standard_normal(len(groups))
    y = (signal + offset + 0.5 * rng.standard_normal(len(groups)) > 0).astype(int)
    return np.column_stack([signal, fingerprint]), y, groups
