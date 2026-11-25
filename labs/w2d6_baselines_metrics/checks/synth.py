"""SYNTHETIC tidy frames in the flowguard schema, for checks only.

They are Gaussian noise with planted shifts. They say nothing about SKAB or real equipment; they
exist so that the contracts of the scorers and metrics can be tested offline and deterministically.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]
SCALES = np.array([0.01, 0.01, 0.5, 0.2, 2.0, 1.0, 10.0, 30.0])
MEANS = np.array([0.2, 0.25, 2.0, 0.1, 80.0, 27.0, 230.0, 100.0])


def frame(x: np.ndarray, anomaly=None, experiment_id="valve1/0", family="valve1") -> pd.DataFrame:
    n = len(x)
    df = pd.DataFrame(x, columns=SENSORS)
    df.insert(0, "datetime", pd.Timestamp("2020-03-09 10:00:00") + pd.to_timedelta(np.arange(n), unit="s"))
    df.insert(0, "t", np.arange(n))
    df.insert(0, "family", family)
    df.insert(0, "experiment_id", experiment_id)
    df["anomaly"] = np.zeros(n, dtype=int) if anomaly is None else np.asarray(anomaly, dtype=int)
    df["changepoint"] = 0
    return df


def normal(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return MEANS + SCALES * rng.standard_normal((n, len(SENSORS)))


def shifted_test(n: int, seed: int, sensor: str = "pressure", sigmas: float = 6.0):
    """Normal rows, the second half shifted by ``sigmas`` standard deviations in one sensor."""
    x = normal(n, seed)
    y = np.zeros(n, dtype=int)
    y[n // 2:] = 1
    j = SENSORS.index(sensor)
    x[n // 2:, j] += sigmas * SCALES[j]
    return frame(x, y)


def correlated(n: int, seed: int, rho: float = 0.95, break_rows: int = 0) -> pd.DataFrame:
    """current and voltage are strongly correlated. In the last ``break_rows`` rows the pair moves
    in OPPOSITE directions by 1.5 sigma each: unremarkable per sensor, impossible jointly."""
    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n, len(SENSORS)))
    i, j = SENSORS.index("current"), SENSORS.index("voltage")
    z[:, j] = rho * z[:, i] + np.sqrt(1 - rho ** 2) * z[:, j]
    y = np.zeros(n, dtype=int)
    if break_rows:
        z[-break_rows:, i] = 1.5 + 0.05 * rng.standard_normal(break_rows)
        z[-break_rows:, j] = -1.5 + 0.05 * rng.standard_normal(break_rows)
        y[-break_rows:] = 1
    return frame(MEANS + SCALES * z, y)


def benchmark_tidy(seed: int = 0, n: int = 120):
    """Six labelled experiments + one reference, a manifest, and a score column whose best-F1
    threshold differs between dev and test (dev anomalies score around 3, test anomalies around 6)."""
    rng = np.random.default_rng(seed)
    frames, scores = [], []
    spec = [("valve1/0", "valve1", "dev", 3.0), ("valve1/1", "valve1", "dev", 3.0),
            ("other/0", "other", "dev", 3.0), ("other/1", "other", "dev", 3.0),
            ("valve1/2", "valve1", "test", 6.0), ("other/2", "other", "test", 6.0)]
    for experiment_id, family, _, level in spec:
        y = np.zeros(n, dtype=int)
        y[n // 2: n // 2 + n // 4] = 1
        frames.append(frame(normal(n, int(rng.integers(1 << 30))), y, experiment_id, family))
        scores.append(np.where(y == 1, level, 0.0) + rng.normal(0, 1.2, n))
    frames.append(frame(normal(n, 99), None, "anomaly-free/anomaly-free", "anomaly-free"))
    scores.append(rng.normal(0, 1.2, n))
    manifest = {
        "version": "v1", "seed": 0, "unit": "experiment_id",
        "test": ["other/2", "valve1/2"],
        "dev_folds": [["valve1/0", "other/0"], ["valve1/1", "other/1"]],
        "reference_normal": ["anomaly-free/anomaly-free"],
        "protocol_b": {"holdout_family": "other"},
    }
    return pd.concat(frames, ignore_index=True), np.concatenate(scores), manifest
