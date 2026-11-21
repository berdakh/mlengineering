import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "checks"))  # harness.py
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

import harness  # noqa: E402
from bugs import BUGS  # noqa: E402

UNIT = "lessons/w1d5_testing_ml_code"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def submitted(target):
    """The learner's (repaired) detect_events."""
    path = target / "eventkit" / "events.py"
    if not path.is_file():
        pytest.fail(f"missing {path}", pytrace=False)
    return _load(path, "submitted_events").detect_events


@pytest.fixture(scope="session")
def reference():
    return _load(HERE / "reference_impl" / "eventkit" / "events.py", "reference_events").detect_events


@pytest.fixture(scope="session")
def grading(target):
    tests_dir = target / "tests"
    if not tests_dir.is_dir() or not list(tests_dir.rglob("test_*.py")):
        pytest.fail(f"no test files found in {tests_dir}", pytrace=False)
    return harness.grade(tests_dir, HERE / "reference_impl", BUGS)
