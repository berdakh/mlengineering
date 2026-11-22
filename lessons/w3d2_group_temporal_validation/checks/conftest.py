"""Fixtures for the w3d2 lab checks. Grades <target>/src/flowguard/validation.py. All data is SYNTHETIC."""
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

UNIT = "lessons/w3d2_group_temporal_validation"


@pytest.fixture(scope="session")
def target() -> Path:
    t = resolve_target(UNIT, "lab")
    assert (t / "src" / "flowguard").is_dir(), f"no package found at {t}/src/flowguard"
    sys.path.insert(0, str(t / "src"))
    return t


@pytest.fixture(scope="session")
def validation(target):
    try:
        return importlib.import_module("flowguard.validation")
    except Exception as exc:  # noqa: BLE001 - report any import problem as a plain failure
        pytest.fail(f"could not import flowguard.validation from {target}/src: {exc!r}", pytrace=False)
