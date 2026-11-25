"""Fixtures for the w3d3 challenge checks. Grades <target>/selection_rule.py, optimism.py, test_looks.json."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w3d3_hyperparameter_selection"
SHIPPED = ROOT / UNIT / "challenge" / "trials.csv"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


def _load(target: Path, name: str):
    path = target / f"{name}.py"
    if not path.is_file():
        pytest.fail(f"{path} not found", pytrace=False)
    spec = importlib.util.spec_from_file_location(f"w3d3_challenge_{name}", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        pytest.fail(f"could not import {path}: {exc!r}", pytrace=False)
    return module


@pytest.fixture(scope="session")
def rule(target):
    return _load(target, "selection_rule")


@pytest.fixture(scope="session")
def optimism(target):
    return _load(target, "optimism")
