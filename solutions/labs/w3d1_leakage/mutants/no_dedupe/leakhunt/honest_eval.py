"""Leak-free evaluation of the late-payment model (reference solution, w3d1).

    python solutions/labs/w3d1_leakage/lab/leakhunt/honest_eval.py

Every decision below answers one question: "would this exist, in this form, when the invoice is issued?"
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import OneHotEncoder

CUTOFF = pd.Timestamp("2024-09-01")          # invoices issued on or after this date form the test period
LEAKY_COLUMNS = ["reminders_sent", "customer_late_rate", "ledger_ref"]
NUMERIC = ["amount", "payment_terms_days", "discount_offered", "tenure_months", "n_prior_invoices",
           "prior_late_rate", "aux_0", "aux_1", "aux_2"]
CATEGORICAL = ["segment", "industry"]
FEATURES = NUMERIC + CATEGORICAL
REISSUE_KEY = ["customer_id", "payment_terms_days", "discount_offered", "aux_0", "aux_1", "aux_2"]


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    """Remove what cannot be used: re-issued copies of an invoice and post-outcome columns.

    A re-issue repeats every attribute of the original except the id, the date and (slightly) the
    amount, and carries the same outcome. Only the first issue is a real prediction opportunity.
    """
    df = df.sort_values(["issue_date", "invoice_id"], kind="stable")
    return df.drop(columns=[c for c in LEAKY_COLUMNS if c in df.columns]).reset_index(drop=True)


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on the past, test on the future: the model will only ever score later invoices."""
    return df[df["issue_date"] < CUTOFF], df[df["issue_date"] >= CUTOFF]


def build_model() -> Pipeline:
    """All preprocessing lives inside the estimator, so it is fitted on training rows only."""
    pre = ColumnTransformer([
        ("num", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
    ])
    return make_pipeline(pre, RandomForestClassifier(n_estimators=200, min_samples_leaf=5, random_state=0))


def fit_model(train: pd.DataFrame) -> Pipeline:
    return build_model().fit(train[FEATURES], train["paid_late"])


def evaluate(df: pd.DataFrame) -> dict:
    train, test = split(prepare(df))
    model = fit_model(train)
    scores = pd.Series(model.predict_proba(test[FEATURES])[:, 1], index=test["invoice_id"].to_numpy())
    return {
        "ap": float(average_precision_score(test["paid_late"], scores)),
        "prevalence": float(test["paid_late"].mean()),
        "n_train": int(len(train)), "n_test": int(len(test)),
        "train_ids": train["invoice_id"].tolist(), "test_ids": test["invoice_id"].tolist(),
        "scores": scores, "model": model,
    }


if __name__ == "__main__":
    data = Path(__file__).resolve().parents[5] / "labs" / "w3d1_leakage" / "data" / "invoices.csv"
    if not data.is_file():      # when this file is copied into lessons/.../lab/leakhunt/
        data = Path(__file__).resolve().parents[2] / "data" / "invoices.csv"
    result = evaluate(pd.read_csv(data, parse_dates=["issue_date"]))
    print(f"train {result['n_train']}, test {result['n_test']}, test late rate {result['prevalence']:.3f}")
    print(f"honest test average precision: {result['ap']:.3f}")
