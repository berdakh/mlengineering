"""w4d1 challenge: promotion detection on SYNTHETIC daily store sales. See challenge/README.md.

Implement the three functions. Keep the signatures; the checks call them on freshly generated data.
Only numpy and pandas are needed (copy what you need from your lab; do not import the lab package).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("seasonal_naive", "ar")


def store_scores(df: pd.DataFrame, method: str, fit_end: str) -> np.ndarray:
    """One anomaly score per row of ``df`` (same order). Per store, in date order; any parameter is
    learned from dates < ``fit_end`` only; a score may use the current and earlier dates only.
    Higher = more likely a promotion day. NaN where no score can be computed."""
    raise NotImplementedError


def choose(df: pd.DataFrame, dev_end: str) -> dict:
    """Return {"method": one of METHODS, "threshold": float, ...} using dates < ``dev_end`` only."""
    raise NotImplementedError


def evaluate(df: pd.DataFrame, dev_end: str, choice: dict) -> dict:
    """Score the dates >= ``dev_end`` once with ``choice``; return at least
    {"precision": float, "recall": float, "f1": float} at the row (day) level."""
    raise NotImplementedError
