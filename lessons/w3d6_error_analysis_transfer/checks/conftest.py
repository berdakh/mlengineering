"""Fixtures for the w3d6 lab checks. Grades <target>/src/flowguard. All data here is SYNTHETIC."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w3d6_error_analysis_transfer"


@pytest.fixture(scope="session")
def ea():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    try:
        return importlib.import_module("flowguard.erroranalysis")
    except Exception as exc:  # noqa: BLE001 - any import problem is reported as a plain failure
        pytest.fail(f"could not import flowguard.erroranalysis from {target}/src: {exc!r}", pytrace=False)
