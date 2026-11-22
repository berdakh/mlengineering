"""Fixtures for the w6d5 challenge checks: grades <target>/plan_fixed.json and <target>/REVIEW.md."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w6d5_cloud_deployment"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def plan(target) -> dict:
    path = target / "plan_fixed.json"
    assert path.is_file(), f"missing {path}"
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        pytest.fail(f"{path} is not valid JSON: {exc}", pytrace=False)


@pytest.fixture(scope="session")
def original() -> dict:
    return json.loads((ROOT / UNIT / "challenge" / "given" / "plan.json").read_text())


@pytest.fixture(scope="session")
def review(target) -> str:
    path = target / "REVIEW.md"
    assert path.is_file(), f"missing {path}"
    return path.read_text()
