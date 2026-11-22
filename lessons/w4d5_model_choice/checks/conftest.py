"""Fixtures for the w4d5 lab checks. Grades <target>/src/flowguard/decision.py. All data is SYNTHETIC."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w4d5_model_choice"


@pytest.fixture(scope="session")
def dec():
    target = resolve_target(UNIT, "lab")
    assert (target / "src" / "flowguard").is_dir(), f"no package found at {target}/src/flowguard"
    sys.path.insert(0, str(target / "src"))
    for name in [m for m in sys.modules if m == "flowguard" or m.startswith("flowguard.")]:
        del sys.modules[name]
    try:
        return importlib.import_module("flowguard.decision")
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import flowguard.decision from {target}/src: {exc!r}", pytrace=False)
