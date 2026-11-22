"""Transfer exercise part 2: LedgerLine late-payment ranking (SYNTHETIC data). Your evaluation.

    python lessons/w3d6_error_analysis_transfer/challenge/evaluate.py

Signatures and return structures are fixed (the checks call them). Everything else is yours:
features, model, baseline, interval method, slices. Add imports and helpers as you need them.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

TEST_START = "2024-10-01"
LABEL_DELAY_DAYS = 30          # `late` is only known 30 days after the due date
CALLS_PER_WEEK = 15
DATA = Path(__file__).resolve().parents[1] / "data" / "invoices.csv"

# The columns your model is allowed to see. Decide for each column of the table whether its value
# exists on the day the invoice is issued. Record the reasoning in REPORT.md (leak audit).
FEATURES: list[str] = []


def load_invoices(path: str | Path = DATA) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["issue_date", "due_date"])


def split_train_test(df: pd.DataFrame, test_start: str = TEST_START) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train, test) as row subsets of ``df``, matching how the model would be used:
    trained once on what is known the day before ``test_start``, then applied to invoices issued
    from ``test_start`` onward."""
    raise NotImplementedError


def weekly_topk_precision(test: pd.DataFrame, scores, k: int = CALLS_PER_WEEK,
                          test_start: str = TEST_START) -> float:
    """The decision metric. Weeks are 7-day blocks counted from ``test_start`` by issue date. Each
    week the team calls the ``k`` highest-scored invoices issued that week (all of them if fewer).
    Return the share of called invoices that turned out late, over the whole period."""
    raise NotImplementedError


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Fit on ``train`` and return one score per row of ``test`` (higher = more likely late)."""
    raise NotImplementedError


def run(df: pd.DataFrame, seed: int = 0) -> dict:
    """The whole evaluation. Return::

        {"test_start": "2024-10-01", "n_train": int, "n_test": int, "test_prevalence": float,
         "baseline": {"name": str, "topk_precision": float},          # a rule needing no model
         "model":    {"name": str, "topk_precision": float, "ci_low": float, "ci_high": float},
         "slices":   [{"slice": str, "n_picked": int, "precision": float}, ...]}   # of the CALLED invoices

    A slice with no called invoices has precision NaN. The interval is yours to justify in REPORT.md.
    """
    raise NotImplementedError


if __name__ == "__main__":
    try:
        result = run(load_invoices())
    except FileNotFoundError as exc:
        sys.exit(f"error: {exc}")
    print(json.dumps(result, indent=2))
