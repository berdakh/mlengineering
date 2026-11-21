"""b1 reference solution: trivial, heuristic and model baselines for monthly churn risk."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

DATA = Path(__file__).resolve().parents[2] / "data"
if not DATA.is_dir():  # this file lives under solutions/; the data lives under diagnostic/
    DATA = Path(__file__).resolve().parents[4] / "diagnostic" / "data"
TARGET = "churned_30d"
CONTACT_FRACTION = 0.10
NUMERIC = ["tenure_days", "monthly_price", "sessions_30d", "avg_session_min",
           "tickets_90d", "failed_payments_90d", "discount_active"]
CATEGORICAL = ["plan", "country", "acquisition_channel"]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    return pd.read_csv(DATA / "churn_train.csv"), pd.read_csv(DATA / "churn_test.csv")


def precision_recall_at_fraction(y_true, scores, fraction: float) -> tuple[float, float]:
    y_true = np.asarray(y_true)
    scores = np.asarray(scores, dtype=float)
    k = math.ceil(fraction * len(y_true))
    top = np.argsort(-scores, kind="stable")[:k]
    hits = float(y_true[top].sum())
    positives = float(y_true.sum())
    return hits / k, (hits / positives if positives else float("nan"))


def trivial_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    return np.full(len(test), train[TARGET].mean())


def heuristic_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    # "Payment trouble first, then low usage": failed payments dominate, fewer sessions break ties.
    return (test["failed_payments_90d"] * 100 - test["sessions_30d"]).to_numpy(dtype=float)


def make_model():
    # All preprocessing lives inside the estimator, so it is fitted on training rows only.
    numeric = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    categorical = make_pipeline(SimpleImputer(strategy="constant", fill_value="missing"),
                                OneHotEncoder(handle_unknown="ignore"))
    pre = ColumnTransformer([("num", numeric, NUMERIC), ("cat", categorical, CATEGORICAL)])
    return make_pipeline(pre, LogisticRegression(max_iter=2000))


def model_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    features = NUMERIC + CATEGORICAL  # customer_id and snapshot_date are deliberately not features
    model = make_model().fit(train[features], train[TARGET])
    return model.predict_proba(test[features])[:, 1]


def summarize(y_true, scores) -> dict:
    precision, recall = precision_recall_at_fraction(y_true, scores, CONTACT_FRACTION)
    return {"ap": float(average_precision_score(y_true, scores)),
            "precision_at_10pct": float(precision), "recall_at_10pct": float(recall)}


def run() -> dict:
    train, test = load_data()
    y = test[TARGET].to_numpy()
    return {"test_prevalence": float(y.mean()),
            "trivial": summarize(y, trivial_scores(train, test)),
            "heuristic": summarize(y, heuristic_scores(train, test)),
            "model": summarize(y, model_scores(train, test))}


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
