"""Fixtures for the w8d3 lab checks: they grade <target>/estimates.py with many varied inputs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w8d3_system_design"


@pytest.fixture(scope="session")
def est():
    path = resolve_target(UNIT, "lab") / "estimates.py"
    spec = importlib.util.spec_from_file_location("w8d3_estimates_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
