"""f5: your corrected evaluation. See ../README.md for the contract."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[2] / "data" / "lapse_export_full.csv"
TARGET = "lapsed_30d"

# Columns of the export that the model is allowed to see at prediction time.
FEATURES: list[str] = []


def load() -> pd.DataFrame:
    """(Provided - do not change.)"""
    return pd.read_csv(DATA)


def make_split(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Positional row indices (train_idx, test_idx) for an evaluation that answers:
    'how well will this model rank accounts on the 1st of a coming month?'"""
    raise NotImplementedError


def build_model():
    """An UNFITTED scikit-learn estimator with fit / predict_proba that accepts the raw
    df[FEATURES] frame (missing values and text categories included)."""
    raise NotImplementedError


def evaluate(df: pd.DataFrame) -> dict:
    """Fit on the train rows, score the test rows. Returns at least
    {"ap": ..., "roc_auc": ..., "n_train": ..., "n_test": ..., "test_prevalence": ...}."""
    raise NotImplementedError


if __name__ == "__main__":
    print(evaluate(load()))
