"""Fixtures for the w8d2 challenge checks: structure and coverage of challenge/REVIEW.md."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w8d2_report_limitations"


@pytest.fixture(scope="session")
def review() -> str:
    path = resolve_target(UNIT, "challenge") / "REVIEW.md"
    assert path.is_file(), f"missing {path}"
    return path.read_text()


@pytest.fixture(scope="session")
def flawed_lines() -> list[str]:
    return (ROOT / UNIT / "challenge" / "FLAWED_REPORT.md").read_text().splitlines()
