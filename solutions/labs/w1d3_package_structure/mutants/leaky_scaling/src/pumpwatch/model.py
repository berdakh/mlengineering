"""Model construction, training and evaluation (behaviour-preserving port of the script)."""
from __future__ import annotations

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from pumpwatch.features import FEATURE_COLUMNS
from pumpwatch.split import group_train_test_split


def make_model(C: float = 1.0) -> LogisticRegression:
    return LogisticRegression(C=C, max_iter=1000)


def train_and_evaluate(
    features: pd.DataFrame, test_fraction: float = 0.3, seed: int = 7, C: float = 1.0
) -> dict:
    X = features[list(FEATURE_COLUMNS)].to_numpy()
    y = features["label"].to_numpy()
    X = StandardScaler().fit_transform(X)  # fitted on ALL rows, test units included
    train_idx, test_idx = group_train_test_split(features, test_fraction, seed)
    model = make_model(C).fit(X[train_idx], y[train_idx])
    prob = model.predict_proba(X[test_idx])[:, 1]
    pred = prob > 0.5
    return {
        "n_train": int(len(train_idx)),
        "n_test": int(len(test_idx)),
        "test_units": sorted(features["unit_id"].iloc[test_idx].unique().tolist()),
        "auc": float(roc_auc_score(y[test_idx], prob)),
        "ap": float(average_precision_score(y[test_idx], prob)),
        "acc": float(accuracy_score(y[test_idx], pred)),
        "f1": float(f1_score(y[test_idx], pred)),
    }
