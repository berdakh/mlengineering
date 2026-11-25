"""Fixtures for the w4d1 challenge checks. Grades <target>/sales_detector.py on SYNTHETIC data that
the checks generate themselves with new seeds, so a solution tuned to the shipped file cannot pass by
memorising it."""
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

import sales_generator  # noqa: E402

UNIT = "labs/w4d1_timeseries_fundamentals"
DEV_END = "2025-07-01"


@pytest.fixture(scope="session")
def det():
    path = resolve_target(UNIT, "challenge") / "sales_detector.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("sales_detector_under_test", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module


@pytest.fixture(scope="session")
def fresh():
    cache = {}

    def make(seed):
        if seed not in cache:
            cache[seed] = sales_generator.simulate(seed=seed)
        return cache[seed].copy()
    return make
