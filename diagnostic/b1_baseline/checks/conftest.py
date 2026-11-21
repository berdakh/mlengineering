import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET_DIR = resolve_target("diagnostic/b1_baseline")
DATA = ROOT / "diagnostic" / "data"


@pytest.fixture(scope="session")
def sub():
    spec = importlib.util.spec_from_file_location("submitted_baseline", TARGET_DIR / "baseline.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def train():
    return pd.read_csv(DATA / "churn_train.csv")


@pytest.fixture()
def test():
    return pd.read_csv(DATA / "churn_test.csv")


@pytest.fixture(scope="session")
def model_scores(sub):
    """Model scores computed once (training may take a few seconds)."""
    return sub.model_scores(pd.read_csv(DATA / "churn_train.csv"), pd.read_csv(DATA / "churn_test.csv"))
