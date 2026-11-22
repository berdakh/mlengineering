"""Tests for interview set 3. Grades interview/set3_work unless SET3_DIR points elsewhere."""
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET3_DIR", ROOT / "interview" / "set3_work")).resolve()


@pytest.fixture(scope="session")
def c9():
    path = TARGET / "c9.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location("set3_c9", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
