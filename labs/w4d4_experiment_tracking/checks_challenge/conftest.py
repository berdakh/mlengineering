"""Fixtures for the w4d4 challenge checks. Grades <target>/compare_groups.py on a SYNTHETIC index."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402


@pytest.fixture(scope="session")
def cg():
    path = resolve_target("labs/w4d4_experiment_tracking", "challenge") / "compare_groups.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("compare_groups_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def index() -> pd.DataFrame:
    """SYNTHETIC registry index. A: trees=200, seeds 0-4. B: trees=50, seeds 0-3 and 7.
    Seed effects are shared (same seed -> similar value), so pairing matters."""
    seed_effect = {0: 0.00, 1: 0.10, 2: -0.05, 3: 0.04, 4: 0.30, 7: -0.30}
    rows = []
    for s in (0, 1, 2, 3, 4):
        rows.append({"run_id": f"a{s}", "status": "complete", "seed": s, "sweep": "iforest",
                     "param.detector.n_estimators": 200, "metric.ap": 0.70 + seed_effect[s] + 0.01 * s})
    for s in (0, 1, 2, 3, 7):
        rows.append({"run_id": f"b{s}", "status": "complete", "seed": s, "sweep": "iforest",
                     "param.detector.n_estimators": 50, "metric.ap": 0.68 + seed_effect[s]})
    rows.append({"run_id": "a5", "status": "partial", "seed": 5, "sweep": "iforest",
                 "param.detector.n_estimators": 200, "metric.ap": 0.99})
    rows.append({"run_id": "b5", "status": "partial", "seed": 5, "sweep": "iforest",
                 "param.detector.n_estimators": 50, "metric.ap": 0.10})
    return pd.DataFrame(rows).sample(frac=1.0, random_state=1).reset_index(drop=True)


@pytest.fixture
def expected():
    diffs = np.array([0.02 + 0.01 * s for s in (0, 1, 2, 3)])
    return diffs
