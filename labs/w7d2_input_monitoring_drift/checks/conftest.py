"""Fixtures for the w7d2 lab checks: grades <target>/src/flowguard/drift.py on SYNTHETIC data."""
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

UNIT = "labs/w7d2_input_monitoring_drift"
SENSORS = ("current", "pressure", "thermocouple", "flow_rate")
CENTRE = {"current": 1.9, "pressure": 0.3, "thermocouple": 25.0, "flow_rate": 32.0}
SCALE = {"current": 0.05, "pressure": 0.02, "thermocouple": 0.3, "flow_rate": 0.8}


@pytest.fixture(scope="session")
def drift():
    src = resolve_target(UNIT, "lab") / "src"
    assert (src / "flowguard" / "drift.py").is_file(), f"no {src}/flowguard/drift.py"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        return importlib.import_module("flowguard.drift")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.drift from {src}: {exc!r}", pytrace=False)


def stable_run(n: int, seed: int, phi: float = 0.9) -> pd.DataFrame:
    """SYNTHETIC stable operation: independent AR(1) noise per sensor around fixed levels (1 Hz)."""
    rng = np.random.default_rng(seed)
    data = {}
    for s in SENSORS:
        e = rng.normal(0, np.sqrt(1 - phi ** 2), n)
        x = np.empty(n)
        x[0] = rng.normal()
        for i in range(1, n):
            x[i] = phi * x[i - 1] + e[i]
        data[s] = CENTRE[s] + SCALE[s] * x
    return pd.DataFrame(data)
