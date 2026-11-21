#!/usr/bin/env python3
"""Self-check for interview set 2 (SQL + pandas).

    python interview/set2_check.py              # check s1, s2, s3, p4 in interview/work/set2
    python interview/set2_check.py s2 p4        # selected prompts
    python interview/set2_check.py --dir PATH   # check answers stored elsewhere

Expected results are computed here with pandas from the raw tables, independently of any SQL.
Column names are ignored, column order matters. Row order matters only for s3.
Exit status 0 if every selected prompt passes.
"""
from __future__ import annotations

import argparse
import importlib.util
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "diagnostic" / "data" / "streambox.db"


def connect() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)   # read-only


def tables() -> dict[str, pd.DataFrame]:
    with connect() as conn:
        return {t: pd.read_sql(f"SELECT * FROM {t}", conn) for t in ("customers", "invoices", "tickets")}


# ----------------------------------------------------------------- expected answers (pandas)
def expected_s1(t) -> list[tuple]:
    tk = t["tickets"].merge(t["customers"][["customer_id", "plan"]], on="customer_id", how="left")
    tk["plan"] = tk["plan"].fillna("anonymous")
    hours = (pd.to_datetime(tk["resolved_at"]) - pd.to_datetime(tk["opened_at"])).dt.total_seconds() / 3600
    tk = tk.assign(hours=hours, is_open=tk["resolved_at"].isna())
    g = tk.groupby(["category", "plan"]).agg(n=("ticket_id", "size"), n_open=("is_open", "sum"), h=("hours", "mean"))
    return [(c, p, int(r.n), int(r.n_open), None if pd.isna(r.h) else float(r.h)) for (c, p), r in g.iterrows()]


def expected_s2(t) -> list[tuple]:
    paid = t["invoices"][t["invoices"]["status"] == "paid"].sort_values(["customer_id", "invoice_date", "invoice_id"])
    paid = paid.assign(rank=paid.groupby("customer_id").cumcount() + 1, cum=paid.groupby("customer_id")["amount"].cumsum())
    third = paid[paid["rank"] == 3]
    return [(r.customer_id, int(r.invoice_id), r.invoice_date, float(r.cum)) for r in third.itertuples()]


def expected_s3(t) -> list[tuple]:
    inv = t["invoices"].assign(month=t["invoices"]["invoice_date"].str[:7])
    paid = inv[inv["status"] == "paid"]
    paid_sets = paid.groupby("month")["customer_id"].agg(set)
    out = []
    for month in sorted(m for m in inv["month"].unique() if m.startswith("2025")):
        previous = (pd.Period(month, "M") - 1).strftime("%Y-%m")
        billed = inv.loc[inv["month"] == month, "customer_id"].nunique()
        now, before = paid_sets.get(month, set()), paid_sets.get(previous, set())
        out.append((month, int(billed), len(now), len(now & before)))
    return out


# ----------------------------------------------------------------- comparison helpers
def same_value(got, want, decimals) -> bool:
    if want is None:
        return got is None
    if isinstance(want, float):
        try:
            return got is not None and abs(float(got) - round(want, decimals)) <= 0.5 * 10 ** -decimals + 1e-9
        except (TypeError, ValueError):
            return False
    if isinstance(want, int):
        try:
            return got is not None and float(got) == want
        except (TypeError, ValueError):
            return False
    return got == want


def compare(got: list[tuple], want: list[tuple], n_keys: int, decimals: int, ordered: bool) -> str | None:
    """Return None if equal, else a short description of the first difference."""
    if got and len(got[0]) != len(want[0]):
        return f"expected {len(want[0])} columns, got {len(got[0])}"
    if not ordered:
        try:
            got, want = sorted(got, key=lambda r: r[:n_keys]), sorted(want, key=lambda r: r[:n_keys])
        except TypeError:
            return "key columns contain values that cannot be ordered (NULL in a key column?)"
    if len(got) != len(want):
        return f"expected {len(want)} rows, got {len(got)}"
    for i, (g, w) in enumerate(zip(got, want)):
        if not all(same_value(a, b, decimals) for a, b in zip(g, w)):
            where = "row" if ordered else "row (after sorting by key)"
            return f"{where} {i}: got {g}, which does not match the expected result for that key/position"
    return None


def run_sql(path: Path) -> list[tuple]:
    sql = path.read_text()
    with connect() as conn:
        return [tuple(r) for r in conn.execute(sql).fetchall()]


# ----------------------------------------------------------------- pandas prompt
def check_p4(path: Path) -> str | None:
    spec = importlib.util.spec_from_file_location("set2_p4", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    fn = module.tickets_90d

    def brute(tickets, snapshots):
        out = []
        for row in snapshots.itertuples():
            lo = row.snapshot_date - pd.Timedelta(days=90)
            mine = tickets[tickets["customer_id"] == row.customer_id]["opened_at"]
            out.append(int(((mine >= lo) & (mine < row.snapshot_date)).sum()))
        return out

    d = pd.Timestamp
    small_t = pd.DataFrame({
        "customer_id": ["A", "A", "A", "A", "B", None, "A"],
        "opened_at": [d("2025-03-03"), d("2025-06-01"), d("2025-05-31 23:59:59"), d("2025-06-01 00:00:01"),
                      d("2025-05-01"), d("2025-05-15"), d("2025-03-02 23:59:59")],
    })
    small_s = pd.DataFrame(
        {"customer_id": ["B", "A", "C", "A"],
         "snapshot_date": [d("2025-06-01"), d("2025-06-01"), d("2025-06-01"), d("2025-03-03")]},
        index=[10, 3, 7, 3],                       # arbitrary, non-unique index
    )
    # A @ 2025-06-01: window [2025-03-03, 2025-06-01): 03-03 in, 05-31 in, 06-01 out, later out, 03-02 out -> 2
    cases = [("boundary case", small_t, small_s, [1, 2, 0, 1])]

    t = tables()
    tk = t["tickets"].assign(opened_at=pd.to_datetime(t["tickets"]["opened_at"]))[["customer_id", "opened_at"]]
    rng = np.random.default_rng(0)
    customers = rng.choice(t["customers"]["customer_id"].to_numpy(), size=400)
    dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, size=400), unit="D")
    snaps = pd.DataFrame({"customer_id": customers, "snapshot_date": dates}, index=rng.permutation(400) + 1000)
    cases.append(("StreamBox sample", tk, snaps, brute(tk, snaps)))

    for name, tickets, snapshots, want in cases:
        t_before, s_before = tickets.copy(deep=True), snapshots.copy(deep=True)
        got = fn(tickets, snapshots)
        if not isinstance(got, pd.Series):
            return f"{name}: expected a pandas Series, got {type(got).__name__}"
        if len(got) != len(snapshots):
            return f"{name}: expected {len(snapshots)} values (one per snapshot row), got {len(got)}"
        if list(got.index) != list(snapshots.index):
            return f"{name}: result index is not the snapshots index in the original order"
        if got.isna().any():
            return f"{name}: result contains missing values (snapshot rows with no tickets must be 0)"
        if [int(v) for v in got.to_numpy()] != want:
            bad = next(i for i, (a, b) in enumerate(zip(got.to_numpy(), want)) if int(a) != b)
            return f"{name}: wrong count at snapshot position {bad}: got {int(got.iloc[bad])}"
        if not tickets.equals(t_before) or not snapshots.equals(s_before):
            return f"{name}: an input DataFrame was modified"
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompts", nargs="*", choices=["s1", "s2", "s3", "p4", []], default=[])
    ap.add_argument("--dir", default=str(ROOT / "interview" / "work" / "set2"))
    args = ap.parse_args()
    target = Path(args.dir).resolve()
    selected = args.prompts or ["s1", "s2", "s3", "p4"]
    t = tables()
    sql_specs = {  # name: (expected, number of key columns, rounding decimals, ordered)
        "s1": (expected_s1, 2, 1, False),
        "s2": (expected_s2, 1, 2, False),
        "s3": (expected_s3, 1, 0, True),
    }
    failures = 0
    for name in selected:
        try:
            if name == "p4":
                problem = check_p4(target / "p4.py")
            else:
                expected, n_keys, decimals, ordered = sql_specs[name]
                problem = compare(run_sql(target / f"{name}.sql"), expected(t), n_keys, decimals, ordered)
        except Exception as exc:  # a broken answer must not crash the checker
            problem = f"{type(exc).__name__}: {exc}"
        print(f"[{'ok' if problem is None else 'FAIL'}] {name}" + ("" if problem is None else f" - {problem}"))
        failures += problem is not None
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
