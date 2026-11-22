import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("lessons/w8d6_final_assessment/f1_python")


@pytest.fixture(scope="session")
def rr():
    """The submitted route_report module, loaded from the directory being graded."""
    spec = importlib.util.spec_from_file_location("submitted_route_report", TARGET / "route_report.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
