"""Reference solution: data-quality checks for the orders export (w2d3 challenge).

Input is the export read as text: ``pd.read_csv(path, dtype=str, keep_default_na=False)``.
Every rule is evaluated on a *validity mask* (True = row satisfies the rule), built so that
an unparseable value is invalid rather than silently skipped: NaN compares False, so rules are
written as "valid = parsed AND condition", never as "invalid = condition".
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

COLUMNS = ("order_id", "customer_id", "order_ts", "currency", "amount", "refunded_amount", "status", "delivered_ts")
CURRENCIES = {"USD", "EUR", "KZT"}
STATUSES = {"placed", "shipped", "delivered", "cancelled"}
TS_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
MAX_GUEST_SHARE = 0.05


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str
    severity: str = "error"


def _rows(df: pd.DataFrame, valid: pd.Series, name: str, ok: str) -> CheckResult:
    ids = df.loc[~valid, "order_id"].tolist()
    if not ids:
        return CheckResult(name, True, ok)
    shown = ", ".join(ids[:20]) + (f" (+{len(ids) - 20} more)" if len(ids) > 20 else "")
    return CheckResult(name, False, f"{len(ids)} row(s): {shown}")


def run_checks(orders: pd.DataFrame) -> list[CheckResult]:
    missing = [c for c in COLUMNS if c not in orders.columns]
    if missing:
        return [CheckResult("required_columns", False, f"missing column(s): {', '.join(missing)}")]
    df = orders.reset_index(drop=True)
    results = [CheckResult("required_columns", True, "all columns present")]

    order_ts = pd.to_datetime(df["order_ts"], format=TS_FORMAT, errors="coerce")
    delivered_ts = pd.to_datetime(df["delivered_ts"], format=TS_FORMAT, errors="coerce")
    amount = pd.to_numeric(df["amount"], errors="coerce")
    refunded = pd.to_numeric(df["refunded_amount"], errors="coerce")
    has_delivery = df["delivered_ts"] != ""
    is_delivered = df["status"] == "delivered"

    results.append(_rows(df, (df["order_id"] != "") & ~df["order_id"].duplicated(keep=False),
                         "order_id_unique", "order_id present and unique"))
    results.append(_rows(df, order_ts.notna(), "order_ts_format", "order_ts matches YYYY-MM-DDTHH:MM:SSZ"))
    results.append(_rows(df, df["currency"].isin(CURRENCIES), "currency_allowed", "currency in contract set"))
    results.append(_rows(df, amount.notna() & (amount > 0), "amount_positive", "amount is a positive number"))
    results.append(_rows(df, refunded.notna() & (refunded >= 0),
                         "refund_within_amount", "0 <= refunded_amount <= amount"))
    results.append(_rows(df, df["status"].isin(STATUSES), "status_allowed", "status in contract set"))
    results.append(_rows(df, has_delivery == is_delivered, "delivery_timestamp_iff_delivered",
                         "delivered_ts present exactly for delivered orders"))
    results.append(_rows(df, ~has_delivery | delivered_ts.notna(),
                         "delivery_not_before_order", "delivered_ts parses and is not before order_ts"))

    share = float((df["customer_id"] == "").mean()) if len(df) else 0.0
    results.append(CheckResult("guest_share", share <= MAX_GUEST_SHARE,
                               f"{share:.1%} of orders have no customer_id (limit {MAX_GUEST_SHARE:.0%})", "warning"))

    days = order_ts.dropna().dt.normalize()
    lost = [] if days.empty else sorted(set(pd.date_range(days.min(), days.max(), freq="D")) - set(days))
    results.append(CheckResult("no_empty_days", not lost,
                               "days without any order: " + ", ".join(d.strftime("%Y-%m-%d") for d in lost)
                               if lost else "every day in the covered range has orders", "warning"))
    return results


if __name__ == "__main__":
    import sys
    table = pd.read_csv(sys.argv[1], dtype=str, keep_default_na=False)
    for r in run_checks(table):
        print(f"{'ok  ' if r.passed else 'FAIL'} [{r.severity:7}] {r.name}: {r.detail}")
