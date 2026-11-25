"""Fixtures for the w3d2 challenge checks. Grades <target>/store_validation.py. SYNTHETIC data only."""
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

UNIT = "labs/w3d2_group_temporal_validation"


@pytest.fixture(scope="session")
def folds_fn():
    path = resolve_target(UNIT, "challenge") / "store_validation.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location("store_validation_under_test", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module.deployment_folds
