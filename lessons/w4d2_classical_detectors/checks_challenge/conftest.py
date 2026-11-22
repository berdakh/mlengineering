"""Fixtures for the w4d2 challenge checks. Grades <target>/fraud.py on SYNTHETIC data generated here
with a seed the shipped files do not use."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

import tx_generator  # noqa: E402

UNIT = "lessons/w4d2_classical_detectors"
SEED = 103


@pytest.fixture(scope="session")
def fraud():
    path = resolve_target(UNIT, "challenge") / "fraud.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("fraud_under_test", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module


@pytest.fixture(scope="session")
def data():
    return tx_generator.tables(SEED)


@pytest.fixture(scope="session")
def result(fraud, data):
    train, _ = data
    return fraud.run(train.copy(), seed=0)
