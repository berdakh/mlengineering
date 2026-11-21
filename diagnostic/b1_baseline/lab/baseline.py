"""b1: baselines for monthly churn risk. Implement the functions; see ../README.md for the contract."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data"
TARGET = "churned_30d"
CONTACT_FRACTION = 0.10  # the retention team can contact 10% of active customers per month


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """(train, test) as prepared by the data team. (Provided - do not change.)"""
    return pd.read_csv(DATA / "churn_train.csv"), pd.read_csv(DATA / "churn_test.csv")


def precision_recall_at_fraction(y_true, scores, fraction: float) -> tuple[float, float]:
    """Precision and recall when the k = ceil(fraction * n) highest-scored rows are flagged."""
    raise NotImplementedError


def trivial_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """No-skill baseline: every test row gets the churn rate observed in `train`."""
    raise NotImplementedError


def heuristic_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """A rule a retention analyst could apply without ML (your choice). Higher = riskier."""
    raise NotImplementedError


def model_scores(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """A simple, defensible first model fitted on `train`; churn-risk score per test row."""
    raise NotImplementedError


def run() -> dict:
    """Evaluate the three baselines on the test set.

    Returns {"test_prevalence": float,
             "trivial": {"ap": ..., "precision_at_10pct": ..., "recall_at_10pct": ...},
             "heuristic": {...same keys...}, "model": {...same keys...}}
    """
    raise NotImplementedError


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2))
