"""Fixtures for the w5d3 challenge checks. Grades <target>/src/flowguard/hysteresis.py and the report."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w5d3_online_inference"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def hyst(target):
    src = target / "src"
    sys.path.insert(0, str(src))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        return importlib.import_module("flowguard.hysteresis")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.hysteresis from {src}: {exc!r}", pytrace=False)
