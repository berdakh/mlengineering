"""Fixtures for the challenge checks: import YOUR challenge/compat.py by path."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE)]

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w5d5_api_testing"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def compat(target):
    path = target / "compat.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("learner_compat", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
