"""Your leak-free evaluation of the late-payment model. Replace every NotImplementedError.

    python labs/w3d1_leakage/lab/leakhunt/honest_eval.py

Contract (the checks call these functions; how you implement them is up to you):

* ``prepare(df)``   -> DataFrame: the export with everything removed that a model must not learn from.
* ``split(df)``     -> (train, test) of a prepared frame. The model will score invoices issued after
                       the export, so the test period is every invoice with issue_date >= CUTOFF.
* ``fit_model(train)`` -> a fitted object with ``predict_proba(frame)``. ``frame`` has the columns of
                       the export; ALL preprocessing must happen inside this object.
* ``evaluate(df)``  -> dict with keys
      "ap"         average precision on the test period (float)
      "n_train", "n_test"
      "train_ids", "test_ids"   lists of invoice_id actually used
      "scores"     pandas Series of test scores indexed by invoice_id
      "model"      the object returned by fit_model
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CUTOFF = pd.Timestamp("2024-09-01")


def prepare(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    raise NotImplementedError


def fit_model(train: pd.DataFrame):
    raise NotImplementedError


def evaluate(df: pd.DataFrame) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    data = Path(__file__).resolve().parents[2] / "data" / "invoices.csv"
    result = evaluate(pd.read_csv(data, parse_dates=["issue_date"]))
    print(f"train {result['n_train']}, test {result['n_test']}")
    print(f"honest test average precision: {result['ap']:.3f}")
