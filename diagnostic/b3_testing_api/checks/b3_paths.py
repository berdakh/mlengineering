"""Locations used by the b3 checks (kept out of conftest.py so the name is unique across sections)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("diagnostic/b3_testing_api")
IMPLS = Path(__file__).resolve().parent / "impls"
