"""The churn table used from Week 5 on: one row per active customer, features from BEFORE a cutoff,
label from the 90 days AFTER it. Week 4 (notebooks 13-16) builds the same table step by step; this is the
ready-made version so later weeks can start from it.

    from mlcourse.churn import build_churn_table, FEATURES
    df = build_churn_table()          # cutoff 2025-06-30, horizon 90 days
    X, y = df[FEATURES], df["churned"]

Definitions (identical to Week 4):
* active customer: at least one non-cancelled order on or before the cutoff;
* churned (label 1): an active customer with no non-cancelled order in (cutoff, cutoff + horizon_days];
* every feature is computed only from rows dated on or before the cutoff (no peeking into the label window).
"""
from __future__ import annotations

import pandas as pd

from mlcourse.sql import sql

DEFAULT_CUTOFF = "2025-06-30"
NUMERIC = ["tenure_days", "n_orders", "total_spent", "avg_order_value", "days_since_last_order",
           "n_tickets", "n_open_tickets", "share_mobile"]
CATEGORICAL = ["segment", "city"]
FEATURES = NUMERIC + CATEGORICAL


def build_churn_table(cutoff: str = DEFAULT_CUTOFF, horizon_days: int = 90, db: str = "shop") -> pd.DataFrame:
    """One row per active customer at `cutoff`, with the features above and the label `churned` (0/1)."""
    c = pd.Timestamp(cutoff)
    customers = sql("SELECT customer_id, signup_date, segment, city FROM customers", db)
    orders = sql("SELECT order_id, customer_id, order_date, status, channel FROM orders", db)
    items = sql("SELECT order_id, quantity, unit_price, discount FROM order_items", db)
    tickets = sql("SELECT customer_id, opened_at, resolved_at FROM support_tickets", db)
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    orders = orders[orders["status"] != "cancelled"]
    items["value"] = items["quantity"] * items["unit_price"] * (1 - items["discount"])
    order_value = items.groupby("order_id")["value"].sum()
    orders = orders.assign(value=orders["order_id"].map(order_value).fillna(0.0))

    before = orders[orders["order_date"] <= c]
    after = orders[(orders["order_date"] > c) & (orders["order_date"] <= c + pd.Timedelta(days=horizon_days))]
    g = before.groupby("customer_id")
    feats = pd.DataFrame({
        "n_orders": g.size(),
        "total_spent": g["value"].sum(),
        "days_since_last_order": (c - g["order_date"].max()).dt.days,
        "share_mobile": g["channel"].apply(lambda s: (s == "mobile_app").mean()),
    })
    feats["avg_order_value"] = feats["total_spent"] / feats["n_orders"]
    t = tickets[pd.to_datetime(tickets["opened_at"]) <= c]
    # a ticket counts as open at the cutoff if it was not resolved by then
    resolved_by_cutoff = pd.to_datetime(t["resolved_at"]) <= c
    feats["n_tickets"] = t.groupby("customer_id").size().reindex(feats.index).fillna(0).astype(int)
    feats["n_open_tickets"] = (t[~resolved_by_cutoff.fillna(False)].groupby("customer_id").size()
                               .reindex(feats.index).fillna(0).astype(int))
    cust = customers.set_index("customer_id").loc[feats.index]
    feats["tenure_days"] = (c - pd.to_datetime(cust["signup_date"])).dt.days
    feats["segment"] = cust["segment"]
    feats["city"] = cust["city"]
    feats["churned"] = (~feats.index.isin(after["customer_id"])).astype(int)
    out = feats.reset_index()[["customer_id", *FEATURES, "churned"]]
    out["total_spent"] = out["total_spent"].round(2)
    out["avg_order_value"] = out["avg_order_value"].round(2)
    return out.sort_values("customer_id").reset_index(drop=True)
