"""Model construction, training and evaluation."""
from __future__ import annotations

import logging

import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from pumpwatch.features import FEATURE_COLUMNS
from pumpwatch.split import group_train_test_split

logger = logging.getLogger(__name__)


def make_model(C: float = 1.0) -> Pipeline:
    """Scaler + logistic regression in ONE estimator.

    Keeping the scaler inside the pipeline means it is fitted on training rows
    only. The original script scaled all rows before splitting (test-set leakage).
    """
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=1000))


def train_and_evaluate(
    features: pd.DataFrame, test_fraction: float = 0.3, seed: int = 7, C: float = 1.0
) -> dict:
    """Fit on the training units, score on the held-out units, return metrics."""
    train_idx, test_idx = group_train_test_split(features, test_fraction, seed)
    X = features[list(FEATURE_COLUMNS)].to_numpy()
    y = features["label"].to_numpy()
    model = make_model(C).fit(X[train_idx], y[train_idx])
    logger.debug("fitted model C=%g coef=%s", C, model[-1].coef_.round(3).tolist())
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
