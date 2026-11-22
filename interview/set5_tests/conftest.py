"""Tests for interview set 5. Grades interview/set5_work unless SET5_DIR points elsewhere."""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET5_DIR", ROOT / "interview" / "set5_work")).resolve()


@pytest.fixture(scope="session")
def c2():
    path = TARGET / "c2.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location("set5_c2", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["set5_c2"] = module      # pydantic resolves annotations through sys.modules
    spec.loader.exec_module(module)
    return module
