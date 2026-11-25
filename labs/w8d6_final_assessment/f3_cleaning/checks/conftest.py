import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("labs/w8d6_final_assessment/f3_cleaning")
RAW = ROOT / "labs" / "w8d6_final_assessment" / "data" / "accounts_dirty.csv"
EXPECTED = Path(__file__).resolve().parent / "expected_clean.csv"


@pytest.fixture(scope="session")
def clean():
    spec = importlib.util.spec_from_file_location("submitted_clean_f3", TARGET / "clean.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.clean


@pytest.fixture()
def raw():
    return pd.read_csv(RAW, dtype=str)


@pytest.fixture(scope="session")
def expected():
    return pd.read_csv(EXPECTED, parse_dates=["signup_date"])


@pytest.fixture(scope="session")
def cleaned(clean):
    return clean(pd.read_csv(RAW, dtype=str)).sort_values("account_id").reset_index(drop=True)
