"""Final transfer task (reference solution): TableTop no-show ranking. SYNTHETIC data.

    python solutions/labs/w8d6_final_assessment/t1_transfer/lab/evaluate.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

TEST_START = "2024-10-01"
CALL_FRACTION = 0.10
DATA = Path(__file__).resolve().parents[2] / "data" / "reservations.csv"
if not DATA.is_file():  # this file lives under solutions/; the data lives under lessons/
    DATA = Path(__file__).resolve().parents[5] / "labs" / "w8d6_final_assessment" / "data" / "reservations.csv"

NUMERIC = ["party_size", "lead_days", "deposit_paid", "prior_visits", "prior_no_shows"]
CATEGORICAL = ["restaurant_id", "slot", "channel"]
DERIVED = ["weekend", "prior_no_show_rate"]
# Leak audit (also in REPORT.md):
#   customer_no_show_rate - mean over the customer's WHOLE history, incl. this and future reservations
#   table_released_at     - filled only when the guest did not come: it is the outcome
#   reminder_reply        - reply to the reminder sent on the service day, after the evening call list
#   reservation_id, customer_id - identifiers; booked_at and service_date are used only via DERIVED
FEATURES: list[str] = NUMERIC + CATEGORICAL + ["service_date"]


def load_reservations(path: str | Path = DATA) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["booked_at", "service_date", "table_released_at"])


def split_train_test(df: pd.DataFrame, test_start: str = TEST_START) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train on reservations served before `test_start` (their outcome is known on that day),
    test on reservations served from `test_start` on - whenever they were booked."""
    start = pd.Timestamp(test_start)
    booked = pd.to_datetime(df["booked_at"])
    return df[booked < start], df[booked >= start]


def daily_topk_precision(test: pd.DataFrame, scores, fraction: float = CALL_FRACTION) -> float:
    """Each evening the team calls the ceil(fraction * n) highest-scored reservations of the next
    service day. Share of called reservations that were no-shows, pooled over all days."""
    frame = pd.DataFrame({"day": pd.to_datetime(test["service_date"]).to_numpy(),
                          "s": np.asarray(scores, dtype=float), "y": test["no_show"].to_numpy()})
    called = []
    for _, g in frame.groupby("day", sort=True):
        k = math.ceil(fraction * len(g))
        called.append(g.sort_values("s", ascending=False, kind="stable").head(k))
    picked = pd.concat(called)
    return float(picked["y"].mean())


def _design(df: pd.DataFrame) -> pd.DataFrame:
    x = df[NUMERIC + CATEGORICAL].copy()
    x["weekend"] = (pd.to_datetime(df["service_date"]).dt.dayofweek >= 4).astype(int)
    x["prior_no_show_rate"] = df["prior_no_shows"] / (df["prior_visits"] + 1)
    return x


def make_model():
    pre = ColumnTransformer([("num", StandardScaler(), NUMERIC + DERIVED),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL)])
    return make_pipeline(pre, LogisticRegression(max_iter=2000))


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    model = make_model().fit(_design(train), train["no_show"])
    return model.predict_proba(_design(test))[:, 1]


def rule_scores(test: pd.DataFrame) -> np.ndarray:
    """No model: no deposit first, then longer lead time."""
    return ((1 - test["deposit_paid"]) * 1000 + test["lead_days"]).to_numpy(dtype=float)


def _called(test: pd.DataFrame, scores, fraction: float) -> pd.DataFrame:
    frame = test.assign(_s=np.asarray(scores, dtype=float))
    parts = []
    for _, g in frame.groupby(pd.to_datetime(frame["service_date"]), sort=True):
        parts.append(g.sort_values("_s", ascending=False, kind="stable").head(math.ceil(fraction * len(g))))
    return pd.concat(parts)


def run(df: pd.DataFrame, seed: int = 0) -> dict:
    train, test = split_train_test(df)
    scores = fit_and_score(train, test)
    called = _called(test, scores, CALL_FRACTION)
    point = float(called["no_show"].mean())
    # Interval: bootstrap over service DAYS (the unit the call list is made for; reservations of one
    # day share the day's conditions). Training is held fixed: it covers test-set sampling only.
    rng = np.random.default_rng(seed)
    per_day = called.groupby(pd.to_datetime(called["service_date"]))["no_show"].agg(["sum", "count"])
    hits, n = per_day["sum"].to_numpy(), per_day["count"].to_numpy()
    boot = []
    for _ in range(2000):
        idx = rng.integers(0, len(per_day), len(per_day))
        boot.append(hits[idx].sum() / n[idx].sum())
    lo, hi = np.percentile(boot, [2.5, 97.5])
    slices = []
    for channel in ["phone", "web", "app", "partner"]:   # slices of the CALLED reservations
        part = called[called["channel"] == channel]
        slices.append({"slice": f"channel={channel}", "n_picked": int(len(part)),
                       "precision": float(part["no_show"].mean()) if len(part) else float("nan")})
    return {"test_start": TEST_START, "n_train": int(len(train)), "n_test": int(len(test)),
            "test_prevalence": float(test["no_show"].mean()),
            "baseline": {"name": "no deposit, then longest lead time",
                         "topk_precision": daily_topk_precision(test, rule_scores(test))},
            "model": {"name": "logistic regression on booking-time features", "topk_precision": point,
                      "ci_low": float(lo), "ci_high": float(hi)},
            "slices": slices}


if __name__ == "__main__":
    print(json.dumps(run(load_reservations(sys.argv[1] if len(sys.argv) > 1 else DATA)), indent=2))
