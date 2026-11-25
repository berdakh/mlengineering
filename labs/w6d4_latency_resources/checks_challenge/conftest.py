"""Fixtures for the w6d4 challenge checks: import <target>/capacity.py and read <target>/CAPACITY.md."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w6d4_latency_resources"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def cap(target):
    path = target / "capacity.py"
    assert path.is_file(), f"no {path}"
    spec = importlib.util.spec_from_file_location("learner_capacity", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
