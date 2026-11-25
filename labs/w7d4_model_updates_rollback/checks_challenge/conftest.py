"""Fixtures for the w7d4 challenge checks: they grade <target>/canary.py and <target>/CANARY.md."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w7d4_model_updates_rollback"
LOGS = ROOT / UNIT / "challenge" / "canary_logs"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def canary(target):
    path = target / "canary.py"
    assert path.is_file(), f"missing {path}"
    spec = importlib.util.spec_from_file_location(f"canary_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
