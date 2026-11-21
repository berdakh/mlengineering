import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

import harness  # noqa: E402
from bugs import BUGS  # noqa: E402

UNIT = "lessons/w1d5_testing_ml_code"


@pytest.fixture(scope="session")
def tests_dir() -> Path:
    return resolve_target(UNIT, "lab") / "tests"


@pytest.fixture(scope="session")
def grading(tests_dir):
    """(reference run, {bug name: run}) - computed once for the whole session."""
    if not tests_dir.is_dir() or not list(tests_dir.rglob("test_*.py")):
        pytest.fail(f"no test files found in {tests_dir}", pytrace=False)
    return harness.grade(tests_dir, HERE / "reference_pkg", BUGS)
