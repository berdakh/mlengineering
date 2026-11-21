import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("diagnostic/a1_python")


@pytest.fixture(scope="session")
def ur():
    """The submitted usage_report module, loaded from the directory being graded."""
    spec = importlib.util.spec_from_file_location("submitted_usage_report", TARGET / "usage_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
