"""Fixtures for the w4d2 lab checks. Grades <target>/src/flowguard/detectors.py. All data is SYNTHETIC."""
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

UNIT = "lessons/w4d2_classical_detectors"


@pytest.fixture(scope="session")
def det():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    try:
        return importlib.import_module("flowguard.detectors")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.detectors from {target}/src: {exc!r}", pytrace=False)


@pytest.fixture
def correlated():
    """SYNTHETIC normal data: two strongly correlated sensors plus three independent ones."""
    rng = np.random.default_rng(0)
    a = rng.standard_normal(3000)
    return pd.DataFrame({"a": a, "b": a + 0.1 * rng.standard_normal(3000),
                         "c": rng.standard_normal(3000), "d": rng.standard_normal(3000),
                         "e": rng.standard_normal(3000)})


@pytest.fixture
def labelled():
    """SYNTHETIC supervised data: the label depends on a non-linear function of two features."""
    rng = np.random.default_rng(1)
    x = rng.standard_normal((4000, 4))
    y = ((x[:, 0] ** 2 + x[:, 1] ** 2) > 2.5).astype(int)
    return pd.DataFrame(x, columns=["f1", "f2", "f3", "f4"]), y
