import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("diagnostic/a3_cleaning")
RAW = ROOT / "diagnostic" / "data" / "signups_dirty.csv"
EXPECTED = Path(__file__).resolve().parent / "expected_clean.csv"


@pytest.fixture(scope="session")
def clean():
    spec = importlib.util.spec_from_file_location("submitted_clean", TARGET / "clean.py")
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
    return clean(pd.read_csv(RAW, dtype=str)).sort_values("customer_id").reset_index(drop=True)
