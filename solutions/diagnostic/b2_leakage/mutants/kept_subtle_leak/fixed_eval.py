"""b2 reference solution: a corrected churn evaluation."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parents[2] / "data" / "churn_export_full.csv"
if not DATA.is_file():  # this file lives under solutions/; the data lives under diagnostic/
    DATA = Path(__file__).resolve().parents[4] / "diagnostic" / "data" / "churn_export_full.csv"
TARGET = "churned_30d"

NUMERIC = ["tenure_days", "monthly_price", "sessions_30d", "avg_session_min",
           "tickets_90d", "failed_payments_90d", "discount_active",
           "last_invoice_offset_days"]
CATEGORICAL = ["plan", "country", "acquisition_channel"]
# Excluded on purpose:
#   retention_offer_sent      - written by the retention tooling AFTER a customer asks to cancel
#   last_invoice_offset_days  - derived from the full invoice history, i.e. from the future
#   customer_id               - an identifier, not a property known to generalise
FEATURES: list[str] = NUMERIC + CATEGORICAL
TEST_FROM = "2025-09-01"  # last four snapshot months are held out


def load() -> pd.DataFrame:
    return pd.read_csv(DATA)


def make_split(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Temporal split: train on snapshots before TEST_FROM, test on later ones.

    The label of the last training snapshot (2025-08-01) closes on 2025-08-31, before the first test
    snapshot, so no training label overlaps the test period.
    """
    date = pd.to_datetime(df["snapshot_date"]).to_numpy()
    is_test = date >= np.datetime64(TEST_FROM)
    return np.flatnonzero(~is_test), np.flatnonzero(is_test)


def build_model():
    # Imputation, scaling and encoding are steps of the estimator, so they are fitted on whatever
    # rows .fit() receives - the training rows - and merely applied to test rows.
    numeric = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    categorical = make_pipeline(SimpleImputer(strategy="constant", fill_value="missing"),
                                OneHotEncoder(handle_unknown="ignore"))
    pre = ColumnTransformer([("num", numeric, NUMERIC), ("cat", categorical, CATEGORICAL)])
    return make_pipeline(pre, LogisticRegression(max_iter=2000))


def evaluate(df: pd.DataFrame) -> dict:
    train_idx, test_idx = make_split(df)
    train, test = df.iloc[train_idx], df.iloc[test_idx]
    model = build_model().fit(train[FEATURES], train[TARGET])
    prob = model.predict_proba(test[FEATURES])[:, 1]
    y = test[TARGET].to_numpy()
    return {"ap": float(average_precision_score(y, prob)), "roc_auc": float(roc_auc_score(y, prob)),
            "n_train": int(len(train)), "n_test": int(len(test)), "test_prevalence": float(y.mean())}


if __name__ == "__main__":
    print(evaluate(load()))
