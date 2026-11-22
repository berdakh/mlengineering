"""Fixtures for the w7d3 challenge checks: they read <target>/monitoring_plan.toml and MONITORING_PLAN.md."""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w7d3_drift_vs_degradation"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def plan(target) -> dict:
    path = target / "monitoring_plan.toml"
    assert path.is_file(), f"missing {path}"
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        pytest.fail(f"monitoring_plan.toml does not parse: {exc}", pytrace=False)
