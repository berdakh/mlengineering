import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET_DIR = resolve_target("diagnostic/b2_leakage")
DATA = ROOT / "diagnostic" / "data" / "churn_export_full.csv"


@pytest.fixture(scope="session")
def sub():
    spec = importlib.util.spec_from_file_location("submitted_fixed_eval", TARGET_DIR / "fixed_eval.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def df():
    return pd.read_csv(DATA)


@pytest.fixture(scope="session")
def split(sub, df):
    import numpy as np
    train_idx, test_idx = sub.make_split(df.copy())
    return np.asarray(train_idx), np.asarray(test_idx)
