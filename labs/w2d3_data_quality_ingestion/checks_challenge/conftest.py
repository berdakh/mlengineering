"""Fixtures for the w2d3 challenge checks. Grades <target>/order_quality.py. Offline; SYNTHETIC inputs."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("labs/w2d3_data_quality_ingestion", "challenge")


@pytest.fixture(scope="session")
def run_checks():
    path = TARGET / "order_quality.py"
    assert path.is_file(), f"{path} not found"
    spec = importlib.util.spec_from_file_location("order_quality", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["order_quality"] = module
    spec.loader.exec_module(module)
    return module.run_checks


def failed(results):
    return [r for r in results if not r.passed]
