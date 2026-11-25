import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET_DIR = resolve_target("lessons/w8d6_final_assessment/f4_baseline")
DATA = ROOT / "lessons" / "w8d6_final_assessment" / "data"


@pytest.fixture(scope="session")
def sub():
    spec = importlib.util.spec_from_file_location("submitted_baseline_f4", TARGET_DIR / "baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def train():
    return pd.read_csv(DATA / "lapse_train.csv")


@pytest.fixture()
def test():
    return pd.read_csv(DATA / "lapse_test.csv")


@pytest.fixture(scope="session")
def model_scores(sub):
    """Model scores computed once."""
    return sub.model_scores(pd.read_csv(DATA / "lapse_train.csv"), pd.read_csv(DATA / "lapse_test.csv"))
