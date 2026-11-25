"""Helpers shared with the lab checks (copied from ../checks/conftest.py; SYNTHETIC data)."""
from __future__ import annotations

import numpy as np
import pandas as pd

SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


def make_samples(n: int = 60, seed: int = 0, shift_at: int | None = 45) -> list[dict]:
    """SYNTHETIC run in the API's JSON shape: 1 Hz, realistic testbed ranges, a flow drop at ``shift_at``."""
    rng = np.random.default_rng(seed)
    centre = {"accelerometer1_rms": 0.21, "accelerometer2_rms": 0.27, "current": 1.9, "pressure": 0.3,
              "temperature": 80.0, "thermocouple": 25.0, "voltage": 230.0, "flow_rate": 32.0}
    times = pd.date_range("2026-03-01 10:00:00", periods=n, freq="1s")
    rows = []
    for i, t in enumerate(times):
        row = {"timestamp": t.isoformat()}
        for s in SENSORS:
            row[s] = float(round(centre[s] * (1 + rng.normal(0, 0.02)), 6))
        if shift_at is not None and i >= shift_at:
            row["flow_rate"] = round(row["flow_rate"] - 8.0, 6)
        rows.append(row)
    return rows


def as_frame(samples: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(samples).rename(columns={"timestamp": "datetime"})
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def error_of(response) -> dict:
    body = response.json()
    assert isinstance(body, dict) and "error" in body, f"error body must be {{'error': {{...}}}}, got {body}"
    err = body["error"]
    for key in ("code", "message", "request_id"):
        assert key in err, f"error body lacks {key!r}: {err}"
    return err
