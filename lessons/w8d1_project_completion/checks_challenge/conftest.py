"""Fixtures for the w8d1 challenge checks: structure of challenge/SCOPING_MEMO.md only."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w8d1_project_completion"


@pytest.fixture(scope="session")
def memo() -> str:
    path = resolve_target(UNIT, "challenge") / "SCOPING_MEMO.md"
    assert path.is_file(), f"missing {path}"
    return path.read_text()
