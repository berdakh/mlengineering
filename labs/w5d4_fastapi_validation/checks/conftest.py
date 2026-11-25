"""Fixtures for the w5d4 lab checks. Grades <target>/src/flowguard/{api,schemas}.py through TestClient.

All data is SYNTHETIC; no network and no downloaded data are used.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w5d4_fastapi_validation"
SENSORS = ("accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate")
N_BURN = 20


@pytest.fixture(scope="session")
def fg():
    target = resolve_target(UNIT, "lab")
    src = target / "src"
    assert (src / "flowguard" / "api.py").is_file(), f"no {src}/flowguard/api.py"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        mods = {n: importlib.import_module(f"flowguard.{n}") for n in ("api", "schemas", "bundle", "inference")}
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard from {src}: {exc!r}", pytrace=False)
    return mods


@pytest.fixture()
def model_dir(fg, tmp_path):
    det = fg["inference"].Detector(n_burn=N_BURN, threshold=3.0, version="synthetic-api-1")
    return fg["bundle"].save_bundle(det, tmp_path / "model")


@pytest.fixture()
def detector(fg, model_dir):
    return fg["bundle"].load_bundle(model_dir)[0]


@pytest.fixture()
def client(fg, model_dir):
    from fastapi.testclient import TestClient
    with TestClient(fg["api"].create_app(model_dir), raise_server_exceptions=False) as c:
        yield c


@pytest.fixture()
def client_without_model(fg, tmp_path):
    from fastapi.testclient import TestClient
    with TestClient(fg["api"].create_app(tmp_path / "does-not-exist"), raise_server_exceptions=False) as c:
        yield c


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
