"""Fixtures for the w6d1 challenge checks (static; no Docker daemon, no network)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w6d1_docker_basics"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")
