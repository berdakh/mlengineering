"""Fixtures for the w4d6 challenge checks: structure of challenge/SUBMISSION.md only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w4d6_project_milestone_1"


@pytest.fixture(scope="session")
def submission() -> str:
    path = resolve_target(UNIT, "challenge") / "SUBMISSION.md"
    assert path.is_file(), f"missing {path}"
    return path.read_text()
