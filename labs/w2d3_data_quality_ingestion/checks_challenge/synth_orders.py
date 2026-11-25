"""SYNTHETIC orders export for the w2d3 challenge (invented shop, invented customers).

    python labs/w2d3_data_quality_ingestion/checks_challenge/synth_orders.py
        rewrites challenge/data/orders_export.csv (the file the learner explores)

Nothing about any real business can be concluded from it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["order_id", "customer_id", "order_ts", "currency", "amount", "refunded_amount", "status", "delivered_ts"]
TS = "%Y-%m-%dT%H:%M:%SZ"
PLANTED = "ORD-900001"       # the row every single-defect case modifies
SENTINEL = "ORD-900002"      # a clean row that must never be blamed


def clean_orders(n: int = 400, days: int = 20, seed: int = 5, guest_share: float = 0.015) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2025-09-01")
    day = np.sort(np.r_[np.arange(days), rng.integers(0, days, n - days)])       # every day has an order
    order_ts = start + pd.to_timedelta(day, unit="D") + pd.to_timedelta(rng.integers(0, 86400, n), unit="s")
    status = rng.choice(["placed", "shipped", "delivered", "cancelled"], n, p=[0.1, 0.15, 0.65, 0.1])
    amount = np.round(rng.lognormal(3.3, 0.6, n), 2) + 1.0
    refunded = np.where(rng.random(n) < 0.06, np.round(amount * rng.uniform(0.1, 1.0, n), 2), 0.0)
    delivered = order_ts + pd.to_timedelta(rng.integers(3600, 6 * 86400, n), unit="s")
    df = pd.DataFrame({
        "order_id": [f"ORD-{100000 + i}" for i in range(n)],
        "customer_id": [f"C{rng.integers(1, 180):05d}" for _ in range(n)],
        "order_ts": order_ts.strftime(TS),
        "currency": rng.choice(["USD", "EUR", "KZT"], n, p=[0.5, 0.3, 0.2]),
        "amount": [f"{a:.2f}" for a in amount],
        "refunded_amount": [f"{r:.2f}" for r in refunded],
        "status": status,
        "delivered_ts": np.where(status == "delivered", delivered.strftime(TS), ""),
    })
    guests = rng.choice(n, int(round(guest_share * n)), replace=False)
    df.loc[guests, "customer_id"] = ""
    # two fixed, clean rows used by the checks
    df.loc[10, ["order_id", "customer_id", "order_ts", "currency", "amount", "refunded_amount", "status", "delivered_ts"]] = \
        [PLANTED, "C00042", "2025-09-03T09:15:00Z", "EUR", "40.00", "0.00", "delivered", "2025-09-05T14:00:00Z"]
    df.loc[11, ["order_id", "customer_id", "order_ts", "currency", "amount", "refunded_amount", "status", "delivered_ts"]] = \
        [SENTINEL, "C00043", "2025-09-03T10:30:00Z", "USD", "25.50", "5.00", "shipped", ""]
    return df[COLUMNS].astype(str)


def with_row(df: pd.DataFrame, **changes: str) -> pd.DataFrame:
    out = df.copy()
    idx = out.index[out["order_id"] == PLANTED][0]
    for col, value in changes.items():
        out.loc[idx, col] = value
    return out


# name -> changes applied to the PLANTED row; all are error-severity contract violations
ROW_DEFECTS = {
    "negative_amount": dict(amount="-40.00"),
    "zero_amount": dict(amount="0.00"),
    "amount_decimal_comma": dict(amount="40,00"),
    "amount_missing": dict(amount=""),
    "refund_exceeds_amount": dict(refunded_amount="55.00"),
    "negative_refund": dict(refunded_amount="-1.00"),
    "currency_lowercase": dict(currency="eur"),
    "currency_unknown": dict(currency="GBP"),
    "status_unknown": dict(status="returned"),
    "delivered_without_timestamp": dict(delivered_ts=""),
    "timestamp_on_undelivered": dict(status="shipped"),
    "delivered_before_ordered": dict(delivered_ts="2025-09-02T08:00:00Z"),
    "order_ts_wrong_format": dict(order_ts="03/09/2025 09:15"),
    "order_ts_impossible": dict(order_ts="2025-13-03T09:15:00Z"),
    "order_id_missing_is_not_tested_here": None,
}
ROW_DEFECTS.pop("order_id_missing_is_not_tested_here")


def duplicate_order(df: pd.DataFrame) -> pd.DataFrame:
    row = df[df["order_id"] == PLANTED].copy()
    row["amount"] = "41.00"
    return pd.concat([df, row], ignore_index=True)


def many_guests(df: pd.DataFrame, share: float = 0.10) -> pd.DataFrame:
    out = df.copy()
    idx = [i for i in out.index if out.loc[i, "order_id"] not in (PLANTED, SENTINEL)]
    out.loc[idx[: int(share * len(out))], "customer_id"] = ""
    return out


def lost_day(df: pd.DataFrame, day: str = "2025-09-12") -> pd.DataFrame:
    return df[~df["order_ts"].str.startswith(day)].reset_index(drop=True)


def export_for_learner() -> pd.DataFrame:
    """The file shipped in challenge/data: the clean table plus a realistic mixture of defects."""
    df = clean_orders(n=600, days=30, seed=11, guest_share=0.07)
    rng = np.random.default_rng(3)
    free = [i for i in df.index if df.loc[i, "order_id"] not in (PLANTED, SENTINEL)]
    pick = iter(rng.choice(free, 60, replace=False).tolist())
    for _ in range(4): df.loc[next(pick), "amount"] = "-" + df.loc[next(pick), "amount"]
    for _ in range(5):
        i = next(pick); df.loc[i, "amount"] = df.loc[i, "amount"].replace(".", ",")
    for _ in range(6):
        i = next(pick); df.loc[i, "currency"] = df.loc[i, "currency"].lower()
    for _ in range(3): df.loc[next(pick), "currency"] = "GBP"
    for _ in range(4):
        i = next(pick); df.loc[i, "refunded_amount"] = f"{float(df.loc[i, 'amount'].replace(',', '.').lstrip('-')) + 10:.2f}"
    for _ in range(3): df.loc[next(pick), "status"] = "returned"
    for _ in range(5):
        i = next(pick); df.loc[i, "status"] = "delivered"; df.loc[i, "delivered_ts"] = ""
    for _ in range(4):
        i = next(pick)
        df.loc[i, "status"] = "delivered"
        df.loc[i, "delivered_ts"] = (pd.to_datetime(df.loc[i, "order_ts"], format=TS) - pd.Timedelta(hours=7)).strftime(TS)
    for _ in range(3):
        i = next(pick); df.loc[i, "order_ts"] = pd.to_datetime(df.loc[i, "order_ts"], format=TS).strftime("%d/%m/%Y %H:%M")
    dup = df.loc[[next(pick) for _ in range(5)]].copy()
    df = pd.concat([df, dup], ignore_index=True)
    df = df[~df["order_ts"].str.startswith("2025-09-17")]
    return df.sample(frac=1.0, random_state=1).reset_index(drop=True)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "challenge" / "data" / "orders_export.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    export_for_learner().to_csv(out, index=False, lineterminator="\n")
    print(f"wrote {out}")
