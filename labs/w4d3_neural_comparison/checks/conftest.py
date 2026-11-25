"""Fixtures for the w4d3 lab checks. Grades <target>/src/flowguard/neural.py. All data is SYNTHETIC.

The checks need PyTorch. Without it every check is SKIPPED with a message; a skip is not a pass.
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

UNIT = "labs/w4d3_neural_comparison"
SENSORS = ["accelerometer1_rms", "accelerometer2_rms", "current", "pressure",
           "temperature", "thermocouple", "voltage", "flow_rate"]

torch = pytest.importorskip(
    "torch", reason="PyTorch is not installed: w4d3 checks are SKIPPED, not passed. "
                    "Install it (see the lesson's set-up note) and rerun.")
torch.set_num_threads(1)   # tiny models run fastest single-threaded; also removes one source of nondeterminism


@pytest.fixture(scope="session")
def neural():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    try:
        return importlib.import_module("flowguard.neural")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.neural from {target}/src: {exc!r}", pytrace=False)


def synthetic_experiment(experiment_id: str, n: int = 260, seed: int = 0, shift_from: int | None = None,
                         shift: float = 6.0, anomaly_value: float | None = None) -> pd.DataFrame:
    """SYNTHETIC SKAB-shaped experiment: 8 correlated sinusoidal sensors plus noise.

    ``shift_from``: rows from this index get +``shift`` (in units of the sensor sd) and anomaly = 1.
    ``anomaly_value``: if given, anomalous rows are set to this absurd value (a contamination probe).
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    base = np.sin(2 * np.pi * t / 25.0)[:, None] * np.linspace(0.5, 1.5, 8)[None, :]
    x = 10.0 + base + 0.2 * rng.standard_normal((n, 8))
    anomaly = np.zeros(n, dtype=int)
    if shift_from is not None:
        x[shift_from:] += shift * x[:60].std(axis=0)
        anomaly[shift_from:] = 1
        if anomaly_value is not None:
            x[shift_from:] = anomaly_value
    df = pd.DataFrame(x, columns=SENSORS)
    df.insert(0, "datetime", pd.date_range("2020-01-01", periods=n, freq="s"))
    df.insert(0, "t", t)
    df.insert(0, "family", experiment_id.split("/")[0])
    df.insert(0, "experiment_id", experiment_id)
    df["anomaly"] = anomaly
    df["changepoint"] = 0
    return df


@pytest.fixture(scope="session")
def frames():
    train = pd.concat([synthetic_experiment(f"valve1/{i}", seed=i) for i in range(3)], ignore_index=True)
    val = synthetic_experiment("valve1/9", seed=9)
    test = synthetic_experiment("valve2/0", seed=20, shift_from=180)
    return train, val, test


def small(neural, **kw):
    params = dict(window=8, bottleneck=2, hidden=8, n_burn=50, seed=0, max_epochs=6, patience=3,
                  batch_size=64, lr=3e-3)
    params.update(kw)
    return neural.NeuralScorer(**params)
