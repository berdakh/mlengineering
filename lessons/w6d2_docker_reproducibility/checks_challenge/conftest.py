"""Fixtures for the w6d2 challenge checks (no network: installs only from the local wheelhouse)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w6d2_docker_reproducibility"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")
