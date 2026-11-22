"""Fixtures for the w3d5 lab checks. Grades <target>/src/flowguard/uncertainty.py. All data is SYNTHETIC."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w3d5_uncertainty"


@pytest.fixture(scope="session")
def unc():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    try:
        return importlib.import_module("flowguard.uncertainty")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.uncertainty from {target}/src: {exc!r}", pytrace=False)
