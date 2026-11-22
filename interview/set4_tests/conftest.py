"""Tests for interview set 4. Grades interview/set4_work unless SET4_DIR points elsewhere."""
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET4_DIR", ROOT / "interview" / "set4_work")).resolve()


@pytest.fixture(scope="session")
def c3():
    path = TARGET / "c3.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location("set4_c3", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
