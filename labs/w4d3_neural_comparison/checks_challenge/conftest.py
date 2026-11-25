"""Fixtures for the w4d3 challenge checks. Grades <target>/seedcompare.py. Numbers are SYNTHETIC."""
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
def sc():
    path = resolve_target("labs/w4d3_neural_comparison", "challenge") / "seedcompare.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("seedcompare_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
