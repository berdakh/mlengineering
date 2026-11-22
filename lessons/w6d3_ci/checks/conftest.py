"""Fixtures for the w6d3 lab checks: parse <target>/.github/workflows/{ci,evaluate}.yml.

The checks read the workflows as data (PyYAML) and assert the contract described in the lesson.
They do not run GitHub Actions; your first push is the real test. If `actionlint` is on PATH it is
run as an extra check.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w6d3_ci"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


@pytest.fixture(scope="session")
def ci(target):
    from wfutil import load_workflow
    return load_workflow(target / ".github" / "workflows" / "ci.yml")


@pytest.fixture(scope="session")
def evaluate(target):
    from wfutil import load_workflow
    return load_workflow(target / ".github" / "workflows" / "evaluate.yml")
