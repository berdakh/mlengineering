"""Final transfer task: TableTop no-show ranking (SYNTHETIC data). Your evaluation.

    python lessons/w8d6_final_assessment/t1_transfer/lab/evaluate.py

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
CALL_FRACTION = 0.10           # 10 % of the next day's reservations, rounded up
DATA = Path(__file__).resolve().parents[2] / "data" / "reservations.csv"

# The columns your model is allowed to see. Decide for each column whether its value exists on the
# evening before the service day. Record the reasoning in REPORT.md (leak audit).
FEATURES: list[str] = []


def load_reservations(path: str | Path = DATA) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["booked_at", "service_date", "table_released_at"])


def split_train_test(df: pd.DataFrame, test_start: str = TEST_START) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (train, test) as row subsets of ``df``, matching how the model would be used:
    trained once on what is known on the evening before ``test_start``, then applied to the
    service days from ``test_start`` onward."""
    raise NotImplementedError


def daily_topk_precision(test: pd.DataFrame, scores, fraction: float = CALL_FRACTION) -> float:
    """The decision metric. For each service day the team calls the ceil(fraction * n) highest-scored
    reservations of that day. Return the share of called reservations that were no-shows, over the
    whole period."""
    raise NotImplementedError


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Fit on ``train`` and return one score per row of ``test`` (higher = more likely no-show)."""
    raise NotImplementedError


def run(df: pd.DataFrame, seed: int = 0) -> dict:
    """The whole evaluation. Return::

        {"test_start": "2024-10-01", "n_train": int, "n_test": int, "test_prevalence": float,
         "baseline": {"name": str, "topk_precision": float},          # a rule needing no model
         "model":    {"name": str, "topk_precision": float, "ci_low": float, "ci_high": float},
         "slices":   [{"slice": str, "n_picked": int, "precision": float}, ...]}   # of the CALLED reservations

    A slice with no called reservations has precision NaN. The interval is yours to justify in REPORT.md.
    """
    raise NotImplementedError


if __name__ == "__main__":
    print(json.dumps(run(load_reservations(sys.argv[1] if len(sys.argv) > 1 else DATA)), indent=2))
