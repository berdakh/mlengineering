"""SYNTHETIC customer-month table for the w2d4 challenge (also used to build challenge/customer_months.csv).

One row per customer per active month. `churn_within_3m` is 1 if the customer cancels in one of the
three months AFTER the row's month; it is missing (NaN) when those three months are not yet all observed.
Nothing about real customers can be concluded from this table.

    python labs/w2d4_problem_framing_splits/checks_challenge/customer_months.py   # rewrites the CSV
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

HORIZON = 3


def make_customer_months(n_customers: int = 300, first: str = "2024-01", n_months: int = 18,
                         seed: int = 0, horizon: int = HORIZON) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    months = pd.period_range(first, periods=n_months, freq="M")
    rows = []
    for c in range(n_customers):
        start = int(rng.integers(0, n_months - 2))
        plan = rng.choice(["basic", "plus", "family"], p=[0.5, 0.3, 0.2])
        base_usage = float(rng.gamma(4.0, 5.0))
        hazard = 0.03 + (0.04 if plan == "basic" else 0.0) + 0.04 * (base_usage < 12)
        churn_at = None
        for i in range(start, n_months):
            if i > start and rng.random() < hazard:
                churn_at = i                       # cancels during month i: no row for month i
                break
            rows.append({"customer_id": f"C{c:04d}", "month": str(months[i]), "tenure_months": i - start,
                         "plan": plan, "usage_hours": round(max(0.0, base_usage + rng.normal(0, 3)), 1),
                         "support_tickets": int(rng.poisson(0.3)), "_i": i, "_churn_at": churn_at})
        for r in rows[::-1]:
            if r["customer_id"] != f"C{c:04d}":
                break
            r["_churn_at"] = churn_at
    df = pd.DataFrame(rows)
    churn_at = df["_churn_at"].astype(float)
    label = ((churn_at > df["_i"]) & (churn_at <= df["_i"] + horizon)).astype(float)
    observed = (df["_i"] + horizon <= n_months - 1) | (label == 1.0)
    df[f"churn_within_{horizon}m"] = label.where(observed)
    return df.drop(columns=["_i", "_churn_at"]).reset_index(drop=True)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "challenge" / "customer_months.csv"
    table = make_customer_months()
    table.to_csv(out, index=False, lineterminator="\n")
    print(f"wrote {out}: {len(table)} rows, {table.customer_id.nunique()} customers, "
          f"label mean {table.churn_within_3m.mean():.3f}, missing labels {int(table.churn_within_3m.isna().sum())}")
