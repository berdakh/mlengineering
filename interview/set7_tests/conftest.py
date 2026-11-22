"""Tests for interview set 7. Grades interview/set7_work unless SET7_DIR points elsewhere."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET7_DIR", ROOT / "interview" / "set7_work")).resolve()


@pytest.fixture(scope="session")
def c2():
    path = TARGET / "c2.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location("set7_c2", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["set7_c2"] = module
    spec.loader.exec_module(module)
    return module


class FakeClock:
    """now() and sleep() for deterministic tests: sleeping advances time; nothing really waits."""

    def __init__(self):
        self.t = 100.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, seconds):
        assert seconds >= 0, f"negative sleep {seconds}"
        self.sleeps.append(seconds)
        self.t += seconds


@pytest.fixture
def clock():
    return FakeClock()
