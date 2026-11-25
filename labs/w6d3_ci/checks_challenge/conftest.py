"""Fixtures for the w6d3 challenge checks. Grades <target>/project and <target>/DIAGNOSIS.md."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "labs" / "w6d3_ci" / "checks"))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w6d3_ci"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def project(target) -> Path:
    p = target / "project"
    assert (p / "pyproject.toml").is_file(), f"no project at {p}"
    return p


@pytest.fixture(scope="session")
def ci(project):
    from wfutil import load_workflow
    return load_workflow(project / ".github" / "workflows" / "ci.yml")
