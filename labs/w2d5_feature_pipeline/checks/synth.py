"""SYNTHETIC tidy frames in the docs/maintainers/flowguard-spec.md schema, for checks only.

Random walks with no physical meaning: they exercise the code paths (several experiments,
a time gap, unequal lengths). They say nothing about real sensor behaviour.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


def make_experiment(experiment_id: str, n: int, seed: int, gap_after: int | None = None,
                    gap_s: float = 90.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    seconds = np.arange(n, dtype=float)
    if gap_after is not None:
        seconds[gap_after + 1:] += gap_s
    frame = pd.DataFrame({
        "experiment_id": experiment_id,
        "family": experiment_id.split("/")[0],
        "t": np.arange(n),
        "datetime": pd.Timestamp("2020-03-09 10:00:00") + pd.to_timedelta(seconds + 1000 * seed, unit="s"),
    })
    for j, sensor in enumerate(SENSORS):
        frame[sensor] = 10.0 * (j + 1) + np.cumsum(rng.normal(0, 0.3, n)) + rng.normal(0, 0.1, n)
    frame["anomaly"] = (np.arange(n) >= int(0.6 * n)).astype(int)
    frame["changepoint"] = 0
    return frame


def make_tidy() -> pd.DataFrame:
    """Three experiments: 80 rows, 120 rows with a 90 s gap after row 49, 70 reference rows."""
    frames = [make_experiment("valve1/0", 80, seed=1),
              make_experiment("valve1/1", 120, seed=2, gap_after=49),
              make_experiment("anomaly-free/anomaly-free", 70, seed=3)]
    frames[2]["anomaly"] = 0
    return pd.concat(frames, ignore_index=True)
