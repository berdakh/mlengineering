"""Fixtures for the w6d4 lab checks: import <target>/loadtest.py. No network; fake `send` functions."""
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
def lt():
    path = resolve_target(UNIT, "lab") / "loadtest.py"
    assert path.is_file(), f"no {path}"
    spec = importlib.util.spec_from_file_location("learner_loadtest", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
