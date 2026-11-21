"""Transfer exercise part 1 - reference solution. Data: SYNTHETIC StreamBox churn snapshots.

    python solutions/lessons/w2d6_baselines_metrics/challenge/offer_policy.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "diagnostic" / "data").is_dir())
DATA = REPO_ROOT / "diagnostic" / "data"
LABEL = "churned_30d"
NUMERIC = ["tenure_days", "monthly_price", "sessions_30d", "avg_session_min", "tickets_90d",
           "failed_payments_90d", "discount_active"]
CATEGORICAL = ["plan", "country", "acquisition_channel"]

OFFER_COST = 4.00         # USD per customer who receives the offer
SUCCESS_RATE = 0.25       # ASSUMED share of would-be churners who stay because of the offer
MONTHS_RETAINED = 6       # ASSUMED months of revenue kept when a save succeeds


def temporal_fit_validation_split(train: pd.DataFrame, n_validation_months: int = 2):
    """Fit on the earlier snapshots, validate on the last ``n_validation_months`` snapshot dates."""
    dates = sorted(train["snapshot_date"].unique())
    if not 0 < n_validation_months < len(dates):
        raise ValueError("n_validation_months must leave at least one month on each side")
    is_validation = train["snapshot_date"].isin(dates[-n_validation_months:])
    return train[~is_validation].copy(), train[is_validation].copy()


def churn_probabilities(fit_df: pd.DataFrame, score_df: pd.DataFrame) -> np.ndarray:
    """P(churn within 30 days) for each row of ``score_df``, from a model fitted on ``fit_df``.

    Plain (unweighted) logistic regression: its fitted probabilities average to the training churn
    rate, which is what a cost-based decision rule needs.
    """
    preprocess = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median"), StandardScaler()), NUMERIC),
        ("cat", make_pipeline(SimpleImputer(strategy="constant", fill_value="missing"),
                              OneHotEncoder(handle_unknown="ignore")), CATEGORICAL),
    ])
    model = make_pipeline(preprocess, LogisticRegression(max_iter=2000))
    model.fit(fit_df[NUMERIC + CATEGORICAL], fit_df[LABEL])
    return model.predict_proba(score_df[NUMERIC + CATEGORICAL])[:, 1]


def brier_score(y_true, p) -> float:
    y, p = np.asarray(y_true, dtype=float), np.asarray(p, dtype=float)
    if y.shape != p.shape:
        raise ValueError("y_true and p differ in length")
    if ((p < 0) | (p > 1)).any():
        raise ValueError("probabilities must lie in [0, 1]")
    return float(np.mean((p - y) ** 2))


def reliability_table(y_true, p, n_bins: int = 10) -> pd.DataFrame:
    """Equal-count bins of predicted probability: n, mean predicted, observed rate per bin."""
    y, p = np.asarray(y_true, dtype=float), np.asarray(p, dtype=float)
    order = np.argsort(p, kind="stable")
    rows = []
    for chunk in np.array_split(order, min(n_bins, len(order))):
        rows.append({"p_low": p[chunk].min(), "p_high": p[chunk].max(), "n": len(chunk),
                     "mean_predicted": p[chunk].mean(), "observed_rate": y[chunk].mean()})
    return pd.DataFrame(rows)


def offer_threshold(monthly_price, offer_cost: float = OFFER_COST, success_rate: float = SUCCESS_RATE,
                    months_retained: int = MONTHS_RETAINED) -> np.ndarray:
    """Smallest churn probability at which the offer has non-negative expected value.

    Expected value of offering = p * success_rate * months_retained * price - offer_cost >= 0
    """
    price = np.asarray(monthly_price, dtype=float)
    return offer_cost / (success_rate * months_retained * price)


def policy_value(y_true, offered, monthly_price, offer_cost: float = OFFER_COST,
                 success_rate: float = SUCCESS_RATE, months_retained: int = MONTHS_RETAINED) -> dict:
    """Net value of offering to the rows where ``offered`` is True, under the stated assumptions."""
    y = np.asarray(y_true, dtype=float)
    offered = np.asarray(offered, dtype=bool)
    price = np.asarray(monthly_price, dtype=float)
    gain = success_rate * months_retained * price * y - offer_cost
    return {
        "n": int(len(y)), "n_offered": int(offered.sum()), "offered_fraction": float(offered.mean()),
        "churners_reached": float(y[offered].sum() / y.sum()) if y.sum() else 0.0,
        "net_value_per_1000": float(gain[offered].sum() / len(y) * 1000.0),
    }


def run() -> dict:
    train = pd.read_csv(DATA / "churn_train.csv")
    test = pd.read_csv(DATA / "churn_test.csv")
    fit, validation = temporal_fit_validation_split(train)
    p_validation = churn_probabilities(fit, validation)
    p_test = churn_probabilities(train, test)
    y, price = test[LABEL].to_numpy(), test["monthly_price"].to_numpy()
    constant = np.full(len(test), train[LABEL].mean())
    policies = {
        "nobody": np.zeros(len(test), dtype=bool),
        "everybody": np.ones(len(test), dtype=bool),
        "prevalence": constant >= offer_threshold(price),
        "model": p_test >= offer_threshold(price),
    }
    return {
        "validation": {"brier_model": brier_score(validation[LABEL], p_validation),
                       "brier_prevalence": brier_score(validation[LABEL], np.full(len(validation), fit[LABEL].mean())),
                       "mean_predicted": float(p_validation.mean()),
                       "observed_rate": float(validation[LABEL].mean())},
        "test": {"brier_model": brier_score(y, p_test), "brier_prevalence": brier_score(y, constant),
                 "mean_predicted": float(p_test.mean()), "observed_rate": float(y.mean())},
        "policies": {name: policy_value(y, offered, price) for name, offered in policies.items()},
        "reliability_test": reliability_table(y, p_test, n_bins=5).round(4).to_dict("records"),
    }


if __name__ == "__main__":
    import json
    report = run()
    print(json.dumps(report, indent=2))
    for success in (0.125, 0.25, 0.5):
        test = pd.read_csv(DATA / "churn_test.csv")
        train = pd.read_csv(DATA / "churn_train.csv")
        p = churn_probabilities(train, test)
        offered = p >= offer_threshold(test["monthly_price"], success_rate=success)
        # decision made believing 0.25, world behaves with `success`:
        believed = p >= offer_threshold(test["monthly_price"])
        print(f"success_rate={success}: optimal-for-that-rate {policy_value(test[LABEL], offered, test['monthly_price'], success_rate=success)['net_value_per_1000']:.1f}"
              f" | policy built for 0.25 {policy_value(test[LABEL], believed, test['monthly_price'], success_rate=success)['net_value_per_1000']:.1f}")
