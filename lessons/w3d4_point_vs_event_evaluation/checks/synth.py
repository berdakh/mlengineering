"""SYNTHETIC tidy frames in the flowguard schema, for checks only. Not SKAB data."""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


def experiment(experiment_id: str, seconds: list[float], anomaly: list[int]) -> pd.DataFrame:
    n = len(seconds)
    frame = pd.DataFrame({
        "experiment_id": experiment_id, "family": experiment_id.split("/")[0], "t": np.arange(n),
        "datetime": pd.Timestamp("2024-01-01") + pd.to_timedelta(seconds, unit="s"),
    })
    for s in SENSORS:
        frame[s] = 0.0
    frame["anomaly"] = anomaly
    frame["changepoint"] = 0
    return frame
