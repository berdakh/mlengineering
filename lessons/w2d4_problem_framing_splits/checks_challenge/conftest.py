"""Fixtures for the w2d4 challenge checks. The table is SYNTHETIC (see customer_months.py)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from tools.wbcheck import resolve_target  # noqa: E402
from customer_months import make_customer_months  # noqa: E402

UNIT = "lessons/w2d4_problem_framing_splits"
TEST_START = "2025-01"


def month_number(months) -> np.ndarray:
    p = pd.PeriodIndex(months, freq="M")
    return np.asarray(p.year * 12 + p.month)


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def split(target):
    path = target / "churn_splits.py"
    assert path.is_file(), f"expected {path}"
    spec = importlib.util.spec_from_file_location("learner_churn_splits", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.split_customer_months


@pytest.fixture(scope="session")
def table() -> pd.DataFrame:
    """A different draw from the file in challenge/, with a shuffled, non-default index."""
    df = make_customer_months(n_customers=400, seed=11).sample(frac=1.0, random_state=3)
    df.index = df.index + 10_000
    return df


class Parts:
    def __init__(self, df: pd.DataFrame, out: dict, horizon: int = 3, start: str = TEST_START):
        assert set(out) >= {"train", "test_known", "test_new"}, f"missing keys, got {sorted(out)}"
        self.df, self.horizon = df, horizon
        self.start = int(month_number([start])[0])
        self.last = int(month_number(df["month"]).max())
        for key in ("train", "test_known", "test_new"):
            labels = list(out[key])
            assert set(labels) <= set(df.index), f"'{key}' must contain labels from df.index"
            assert len(labels) == len(set(labels)), f"'{key}' contains repeated rows"
            setattr(self, key, df.loc[labels])
        self.m = lambda part: month_number(part["month"])


@pytest.fixture(scope="session")
def parts(split, table) -> Parts:
    return Parts(table, split(table, TEST_START, horizon_months=3, new_customer_fraction=0.2, seed=0))
