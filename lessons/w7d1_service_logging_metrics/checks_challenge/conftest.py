"""Fixtures for the w7d1 challenge checks: grades <target>/slo.py and <target>/SLO.md."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w7d1_service_logging_metrics"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def slo(target):
    path = target / "slo.py"
    assert path.is_file(), f"no {path}"
    spec = importlib.util.spec_from_file_location("learner_slo", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def access(status: int, ms: float = 10.0, route: str = "/predict") -> dict:
    return {"event": "access", "route": route, "status": status, "duration_ms": ms}
