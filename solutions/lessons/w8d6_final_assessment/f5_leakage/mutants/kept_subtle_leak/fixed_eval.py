"""f5 reference solution: a corrected lapse evaluation."""
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

DATA = Path(__file__).resolve().parents[2] / "data" / "lapse_export_full.csv"
if not DATA.is_file():  # this file lives under solutions/; the data lives under lessons/
    DATA = (Path(__file__).resolve().parents[5] / "lessons" / "w8d6_final_assessment" / "data"
            / "lapse_export_full.csv")
TARGET = "lapsed_30d"

NUMERIC = ["tenure_days", "monthly_fee", "employees", "shipments_30d", "avg_parcel_kg",
           "complaints_90d", "lost_parcels_90d", "promo_active"]
CATEGORICAL = ["tier", "region", "sales_channel"]
# Excluded on purpose:
#   winback_call_logged       - written by the CRM AFTER an account has lapsed or announced it
#   last_pickup_offset_days   - days to the account's LAST EVER pickup: computed from future shipments
#   account_id                - an identifier, not a property known to generalise
FEATURES: list[str] = NUMERIC + CATEGORICAL + ["last_pickup_offset_days"]
TEST_FROM = "2025-09-01"  # the last four snapshot months are held out


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
