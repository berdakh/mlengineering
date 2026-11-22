"""Transfer exercise part 2 - reference solution. LedgerLine late-payment ranking (SYNTHETIC data).

    python solutions/lessons/w3d6_error_analysis_transfer/challenge/evaluate.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TEST_START = "2024-10-01"
LABEL_DELAY_DAYS = 30          # `late` is only known 30 days after the due date
CALLS_PER_WEEK = 15
DATA = Path(__file__).resolve().parents[4] / "lessons" / "w3d6_error_analysis_transfer" / "data" / "invoices.csv"
if not DATA.is_file():         # when this file is copied into lessons/.../challenge/
    DATA = Path(__file__).resolve().parents[1] / "data" / "invoices.csv"

# Columns knowable on the day the invoice is issued. Excluded on purpose:
#   days_to_payment, reminders_sent  - happen after the due date (they are the outcome in other clothes)
#   customer_late_rate               - computed at export over ALL the customer's invoices, future ones included
#   account_status                   - snapshot at export time, set by late payments in H2 2024
FEATURES = ["segment", "industry", "country", "payment_terms_days", "amount",
            "prior_resolved_invoices", "prior_late_invoices"]
_CATEGORICAL = ["segment", "industry", "country"]


def load_invoices(path: str | Path = DATA) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["issue_date", "due_date"])


def split_train_test(df: pd.DataFrame, test_start: str = TEST_START) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Test = invoices issued on or after ``test_start``. Train = invoices whose outcome was already
    KNOWN the day before: due date + 30 days earlier than ``test_start``."""
    cutoff = pd.Timestamp(test_start)
    test = df[df["issue_date"] >= cutoff]
    known = df["due_date"] + pd.Timedelta(days=LABEL_DELAY_DAYS) < cutoff
    train = df[known & (df["issue_date"] < cutoff)]
    return train, test


def weekly_topk_precision(test: pd.DataFrame, scores, k: int = CALLS_PER_WEEK,
                          test_start: str = TEST_START) -> float:
    """Share of late invoices among those called: each week (7-day blocks from ``test_start``) the
    ``k`` highest-scored invoices issued that week are called (all of them if fewer than ``k``)."""
    picked = _picked(test, scores, k, test_start)
    return float(picked["late"].mean()) if len(picked) else float("nan")


def _picked(test: pd.DataFrame, scores, k: int, test_start: str) -> pd.DataFrame:
    frame = test.assign(_score=np.asarray(scores, dtype=float),
                        _week=(test["issue_date"] - pd.Timestamp(test_start)).dt.days // 7)
    return frame.sort_values("_score", ascending=False, kind="stable").groupby("_week", sort=True).head(k)


def _design(frame: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    x = pd.get_dummies(frame[FEATURES], columns=_CATEGORICAL, dtype=float)
    x["log_amount"] = np.log(frame["amount"].to_numpy())
    # shrunk prior late rate: (late + 0.5) / (resolved + 2); 0.25 for a customer with no resolved history
    x["prior_late_rate"] = (frame["prior_late_invoices"] + 0.5) / (frame["prior_resolved_invoices"] + 2.0)
    x["customer_history_score"] = frame["customer_late_rate"].to_numpy()
    x = x.drop(columns=["amount"])
    return x if columns is None else x.reindex(columns=columns, fill_value=0.0)


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Fit on ``train`` (features and its labels only) and return one score per row of ``test``."""
    x_train = _design(train)
    model = make_pipeline(StandardScaler(), LogisticRegression(C=0.5, max_iter=3000))
    model.fit(x_train, train["late"])
    return model.predict_proba(_design(test, list(x_train.columns)))[:, 1]


def prior_rate_rule(test: pd.DataFrame) -> np.ndarray:
    """The rule a collections team would use without a model: call customers with a bad record."""
    return ((test["prior_late_invoices"] + 0.5) / (test["prior_resolved_invoices"] + 2.0)).to_numpy()


def _customer_bootstrap(picked: pd.DataFrame, n_boot: int, seed: int) -> tuple[float, float]:
    """Percentile interval for precision among called invoices, resampling CUSTOMERS."""
    per_customer = picked.groupby("customer_id")["late"].agg(["sum", "count"]).to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(per_customer), size=(n_boot, len(per_customer)))
    values = per_customer[draws, 0].sum(axis=1) / per_customer[draws, 1].sum(axis=1)
    low, high = np.quantile(values, [0.025, 0.975])
    return float(low), float(high)


def run(df: pd.DataFrame, seed: int = 0, n_boot: int = 2000) -> dict:
    train, test = split_train_test(df)
    scores = fit_and_score(train, test)
    picked = _picked(test, scores, CALLS_PER_WEEK, TEST_START)
    low, high = _customer_bootstrap(picked, n_boot, seed)
    slices = []
    for segment in sorted(df["segment"].unique()):
        part = picked[picked["segment"] == segment]
        slices.append({"slice": segment, "n_picked": int(len(part)),
                       "n_customers": int(part["customer_id"].nunique()),
                       "precision": float(part["late"].mean()) if len(part) else float("nan")})
    return {
        "test_start": TEST_START, "n_train": int(len(train)), "n_test": int(len(test)),
        "test_prevalence": float(test["late"].mean()),
        "baseline": {"name": "prior late-rate rule",
                     "topk_precision": weekly_topk_precision(test, prior_rate_rule(test))},
        "model": {"name": "logistic regression", "topk_precision": float(picked["late"].mean()),
                  "ci_low": low, "ci_high": high},
        "slices": slices,
    }


if __name__ == "__main__":
    try:
        result = run(load_invoices())
    except FileNotFoundError as exc:
        sys.exit(f"error: {exc}")
    print(json.dumps(result, indent=2))
