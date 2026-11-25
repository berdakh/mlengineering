"""Locations used by the f6 checks (kept out of conftest.py so the name is unique across sections)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("labs/w8d6_final_assessment/f6_testing_api")
IMPLS = Path(__file__).resolve().parent / "impls"
