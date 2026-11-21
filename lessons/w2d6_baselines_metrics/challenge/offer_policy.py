"""Transfer exercise part 1 - YOUR work. Data: SYNTHETIC StreamBox churn snapshots.

    python lessons/w2d6_baselines_metrics/challenge/offer_policy.py

Read challenge/README.md first. Signatures and return types are the contract; everything else is yours.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "diagnostic" / "data").is_dir())
DATA = REPO_ROOT / "diagnostic" / "data"
LABEL = "churned_30d"

OFFER_COST = 4.00         # USD per customer who receives the offer
SUCCESS_RATE = 0.25       # ASSUMED share of would-be churners who stay because of the offer
MONTHS_RETAINED = 6       # ASSUMED months of revenue kept when a save succeeds


def temporal_fit_validation_split(train: pd.DataFrame, n_validation_months: int = 2):
    """Return (fit, validation): validation is the last ``n_validation_months`` snapshot dates."""
    raise NotImplementedError


def churn_probabilities(fit_df: pd.DataFrame, score_df: pd.DataFrame) -> np.ndarray:
    """P(churn within 30 days) for each row of ``score_df``, from a model fitted on ``fit_df`` only.

    Must work when ``score_df`` has no label column. Values in [0, 1]. Deterministic.
    """
    raise NotImplementedError


def brier_score(y_true, p) -> float:
    """Mean squared difference between predicted probability and outcome."""
    raise NotImplementedError


def reliability_table(y_true, p, n_bins: int = 10) -> pd.DataFrame:
    """Equal-COUNT bins of predicted probability, ordered from lowest to highest.

    Columns: p_low, p_high, n, mean_predicted, observed_rate. Every row belongs to exactly one bin.
    """
    raise NotImplementedError


def offer_threshold(monthly_price, offer_cost: float = OFFER_COST, success_rate: float = SUCCESS_RATE,
                    months_retained: int = MONTHS_RETAINED) -> np.ndarray:
    """Per-customer churn probability above which sending the offer has non-negative expected value."""
    raise NotImplementedError


def policy_value(y_true, offered, monthly_price, offer_cost: float = OFFER_COST,
                 success_rate: float = SUCCESS_RATE, months_retained: int = MONTHS_RETAINED) -> dict:
    """Value of offering to the rows where ``offered`` is True, under the stated assumptions.

    Returns {"n", "n_offered", "offered_fraction", "churners_reached", "net_value_per_1000"} where
    net value sums, over offered rows, (success_rate * months_retained * price if the customer would
    have churned, else 0) minus offer_cost, scaled to 1,000 customers in the population.
    """
    raise NotImplementedError


def run() -> dict:
    """Fit on churn_train.csv, evaluate on churn_test.csv. Returns::

        {"validation": {"brier_model", "brier_prevalence", "mean_predicted", "observed_rate"},
         "test":       {"brier_model", "brier_prevalence", "mean_predicted", "observed_rate"},
         "policies":   {"nobody": policy_value(...), "everybody": ..., "prevalence": ..., "model": ...}}

    "prevalence" is the policy of a model that predicts the training churn rate for everyone.
    """
    raise NotImplementedError


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, default=str))
