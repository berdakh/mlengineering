"""Fixtures for the w7d4 lab checks. They grade <target>/src/flowguard/update.py on SYNTHETIC runs and
bundles built here in temporary directories; no downloaded data and no network are needed."""
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

UNIT = "lessons/w7d4_model_updates_rollback"
SERVING = ["datetime", "flow_rate", "pressure", "current"]


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def fg(target):
    """The flowguard package from the target lab (fresh import)."""
    src = str(target / "src")
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    sys.path.insert(0, src)
    mods = {n: importlib.import_module(f"flowguard.{n}") for n in ("update", "models", "registry", "serving", "api")}
    sys.path.remove(src)
    return mods


def make_run(seed: int = 0, n: int = 600, fault=(350, 450), drop=5.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    flow = 32 + 0.4 * rng.standard_normal(n)
    flow[fault[0]:fault[1]] -= drop
    return pd.DataFrame({"datetime": pd.Timestamp("2027-01-01") + pd.to_timedelta(np.arange(n), "s"),
                         "flow_rate": flow, "pressure": 1 + 0.01 * rng.standard_normal(n),
                         "current": 2 + 0.05 * rng.standard_normal(n)})


@pytest.fixture
def registry(fg, tmp_path):
    """A registry with flowguard 1.0.0 (threshold 6), 1.1.0 (threshold 4) and 2.0.0 (needs voltage)."""
    models, reg = fg["models"], fg["registry"]
    root = tmp_path / "registry"
    specs = [("1.0.0", ("flow_rate",), 6.0), ("1.1.0", ("flow_rate",), 4.0), ("2.0.0", ("flow_rate", "voltage"), 6.0)]
    for version, sensors, thr in specs:
        m = models.BurnInZ(name="flowguard", version=version, sensors=sensors, threshold=thr, min_duration=5, merge_gap=2)
        reg.register(root, reg.save_bundle(m, tmp_path / "bundles" / version))
    return root
