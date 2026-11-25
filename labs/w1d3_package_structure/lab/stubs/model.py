"""Model construction, training and evaluation."""
from __future__ import annotations

import pandas as pd


def make_model(C: float = 1.0):
    """Return an UNFITTED scikit-learn estimator with fit / predict_proba.

    Task 4: a faithful port (whatever the script did).
    Task 7: the estimator must take raw, unscaled features.
    """
    raise NotImplementedError


def train_and_evaluate(
    features: pd.DataFrame, test_fraction: float = 0.3, seed: int = 7, C: float = 1.0
) -> dict:
    """Fit on training units, score on held-out units.

    Return a JSON-serialisable dict with at least:
    n_train, n_test, test_units (sorted list of str), auc, ap, acc, f1.
    """
    raise NotImplementedError
