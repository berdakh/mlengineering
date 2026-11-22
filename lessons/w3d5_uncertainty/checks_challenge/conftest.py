"""Fixtures for the w3d5 challenge checks. Grades <target>/power.py. All data is SYNTHETIC."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402


@pytest.fixture(scope="session")
def pw():
    path = resolve_target("lessons/w3d5_uncertainty", "challenge") / "power.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("w3d5_power", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module
