"""Fixtures for the w4d1 lab checks. Grades <target>/src/flowguard/forecast.py. All data is SYNTHETIC."""
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

UNIT = "labs/w4d1_timeseries_fundamentals"


@pytest.fixture(scope="session")
def fc():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    try:
        return importlib.import_module("flowguard.forecast")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.forecast from {target}/src: {exc!r}", pytrace=False)


def simulate_ar(phi, n, mean=0.0, sigma=1.0, seed=0, burn=500):
    """SYNTHETIC stationary AR(p) series with the given mean and innovation standard deviation."""
    rng = np.random.default_rng(seed)
    p = len(phi)
    e = rng.normal(0.0, sigma, n + burn)
    x = np.zeros(n + burn)
    for t in range(p, n + burn):
        x[t] = sum(phi[k] * x[t - 1 - k] for k in range(p)) + e[t]
    return x[burn:] + mean


@pytest.fixture
def ar():
    return simulate_ar


@pytest.fixture
def tidy_factory():
    """Tiny SYNTHETIC tidy frames in the project schema (two sensors used)."""
    def make(n_exp=3, n=200, seed=0):
        rng = np.random.default_rng(seed)
        frames = []
        for i in range(n_exp):
            a = simulate_ar([0.7], n, mean=5.0 + i, seed=seed + 10 * i)
            b = simulate_ar([0.3, 0.2], n, mean=-2.0, seed=seed + 10 * i + 1)
            frames.append(pd.DataFrame({
                "experiment_id": f"valve1/{i}", "family": "valve1", "t": np.arange(n),
                "flow_rate": a, "pressure": b, "anomaly": 0,
            }))
        df = pd.concat(frames, ignore_index=True)
        return df.sample(frac=1.0, random_state=seed).reset_index(drop=True)   # rows deliberately shuffled
    return make
