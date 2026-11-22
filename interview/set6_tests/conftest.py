"""Tests for interview set 6. Grades interview/set6_work unless SET6_DIR points elsewhere."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET6_DIR", ROOT / "interview" / "set6_work")).resolve()


@pytest.fixture(scope="session")
def c3():
    path = TARGET / "c3.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location("set6_c3", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["set6_c3"] = module
    spec.loader.exec_module(module)
    return module
