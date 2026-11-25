"""Fixtures for the w2d6 challenge checks. Grades <target>/offer_policy.py on SYNTHETIC StreamBox data."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w2d6_baselines_metrics"
DATA = ROOT / "diagnostic" / "data"


@pytest.fixture(scope="session")
def mod():
    path = resolve_target(UNIT, "challenge") / "offer_policy.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location("offer_policy_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def train():
    return pd.read_csv(DATA / "churn_train.csv")


@pytest.fixture(scope="session")
def test():
    return pd.read_csv(DATA / "churn_test.csv")


@pytest.fixture(scope="session")
def report(mod):
    return mod.run()
