"""Shared fixtures: an app built from a SYNTHETIC bundle in a temp dir, and SYNTHETIC samples."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from flowguard.api import create_app
from flowguard.bundle import save_bundle
from flowguard.inference import Detector

N_BURN = 20
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")


@pytest.fixture()
def model_dir(tmp_path):
    return save_bundle(Detector(n_burn=N_BURN, threshold=3.0, version="test-1"), tmp_path / "model")


@pytest.fixture()
def client(model_dir):
    with TestClient(create_app(model_dir), raise_server_exceptions=False) as c:
        yield c


def make_samples(n: int = 60, seed: int = 0, shift_at: int | None = 45) -> list[dict]:
    """SYNTHETIC 1 Hz run with a flow drop at ``shift_at``."""
    rng = np.random.default_rng(seed)
    centre = {"accelerometer1_rms": 0.21, "accelerometer2_rms": 0.27, "current": 1.9, "pressure": 0.3,
              "temperature": 80.0, "thermocouple": 25.0, "voltage": 230.0, "flow_rate": 32.0}
    rows = []
    for i, t in enumerate(pd.date_range("2026-03-01 10:00:00", periods=n, freq="1s")):
        row = {"timestamp": t.isoformat(), **{s: float(centre[s] * (1 + rng.normal(0, 0.02))) for s in SENSORS}}
        if shift_at is not None and i >= shift_at:
            row["flow_rate"] -= 8.0
        rows.append(row)
    return rows
