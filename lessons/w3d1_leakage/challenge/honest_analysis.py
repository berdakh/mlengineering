"""Your replacement for published_analysis.py. Implement honest_estimate.

Contract (graded by checks_challenge/):
    honest_estimate(X, y, seed=0) -> {"auc": float, "model": fitted object with predict_proba(DataFrame)}

* "auc" is your estimate of the ROC AUC the returned model will have on NEW leads.
* The model may use feature selection and tuning; every data-dependent step must be inside
  whatever procedure produces the estimate.
* Same inputs and seed -> same output.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def honest_estimate(X: pd.DataFrame, y: pd.Series, seed: int = 0) -> dict:
    raise NotImplementedError


if __name__ == "__main__":
    data = pd.read_csv(Path(__file__).resolve().parent / "leads.csv")
    result = honest_estimate(data.drop(columns="converted"), data["converted"])
    print(f"honest AUC estimate: {result['auc']:.3f}")
