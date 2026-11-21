"""Tests for interview set 1. Grades interview/work/set1 unless SET1_DIR points elsewhere."""
import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TARGET = Path(os.environ.get("SET1_DIR", ROOT / "interview" / "work" / "set1")).resolve()


def load(name: str):
    path = TARGET / f"{name}.py"
    if not path.is_file():
        pytest.fail(f"missing {path}")
    spec = importlib.util.spec_from_file_location(f"set1_{name}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def target_dir():
    return TARGET
