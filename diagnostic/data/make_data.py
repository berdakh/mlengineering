"""Generate the SYNTHETIC "StreamBox" subscription dataset used by the diagnostic.

Everything here is simulated from the seeded process below. It exists so the
diagnostic has known, planted properties (data-quality defects, a join fan-out,
leaky columns). Model scores obtained on it say nothing about real churn.

    python diagnostic/data/make_data.py            # (re)write all files
    python diagnostic/data/make_data.py --check    # regenerate in memory, compare with files on disk

Outputs (see diagnostic/data/README.md for schemas):
    streambox.db              SQLite: customers, invoices, tickets          (a2_sql)
    signups_dirty.csv         dirty CRM export                              (a3_cleaning)
    churn_train.csv / churn_test.csv   monthly snapshots, prepared split    (b1_baseline)
    churn_export_full.csv     monthly snapshots incl. extra export columns  (b2_leakage)
    ../a3_cleaning/checks/expected_clean.csv   ground truth for the cleaning checks
"""
from __future__ import annotations

import argparse
import hashlib
import io
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20261122
N_CUSTOMERS = 900
HERE = Path(__file__).resolve().parent
EXPECTED_CLEAN = HERE.parent / "a3_cleaning" / "checks" / "expected_clean.csv"
PRICES = {"basic": 9.99, "standard": 14.99, "premium": 19.99}
BASIC_PRICE_AFTER_INCREASE = 11.99
PRICE_INCREASE = pd.Timestamp("2025-09-01")
SNAPSHOTS = pd.date_range("2025-01-01", "2025-12-01", freq="MS")
BILLING_MONTHS = pd.date_range("2024-01-01", "2025-12-01", freq="MS")
TRAIN_END = pd.Timestamp("2025-08-01")  # b1: train = snapshots up to and including this date


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + np.exp(-z))


def simulate(seed: int = SEED) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # ---------------------------------------------------------------- customers
    ids = [f"C{i:05d}" for i in range(1, N_CUSTOMERS + 1)]
    span = (pd.Timestamp("2025-10-31") - pd.Timestamp("2023-01-01")).days
    signup = pd.Timestamp("2023-01-01") + pd.to_timedelta(rng.integers(0, span + 1, N_CUSTOMERS), unit="D")
    country = rng.choice(["US", "DE", "KZ", "BR", "IN"], N_CUSTOMERS, p=[0.35, 0.2, 0.15, 0.15, 0.15]).astype(object)
    country[rng.random(N_CUSTOMERS) < 0.04] = None
    plan = rng.choice(["basic", "standard", "premium"], N_CUSTOMERS, p=[0.5, 0.3, 0.2])
    channel = rng.choice(["organic", "paid_search", "referral", "partner"], N_CUSTOMERS, p=[0.4, 0.3, 0.2, 0.1])
    engagement = rng.standard_normal(N_CUSTOMERS)  # latent, never exported
    age = rng.integers(18, 76, N_CUSTOMERS)
    customers = pd.DataFrame({
        "customer_id": ids, "signup_date": signup, "country": country,
        "plan": plan, "acquisition_channel": channel,
    })

    # ------------------------------------------- monthly simulation per customer
    invoices, tickets, snaps = [], [], []
    for i, cid in enumerate(ids):
        e, s_date, pl = engagement[i], signup[i], plan[i]
        failed_hist: list[tuple[pd.Timestamp, bool]] = []
        ticket_times: list[pd.Timestamp] = []
        churn_date = None
        cust_invoices = []
        for m in BILLING_MONTHS:
            if m <= s_date:
                continue
            price = BASIC_PRICE_AFTER_INCREASE if (pl == "basic" and m >= PRICE_INCREASE) else PRICES[pl]
            # --- snapshot on the 1st of each 2025 month, BEFORE this month's invoice is known
            if m >= SNAPSHOTS[0]:
                tenure = (m - s_date).days
                sessions = int(rng.poisson(np.exp(2.2 + 0.5 * e + 0.3 * rng.standard_normal())))
                avg_min = float(np.round(rng.gamma(4.0, 6.0 * np.exp(0.2 * e)), 1))
                if rng.random() < 0.03:
                    avg_min = np.nan
                t90 = sum(1 for t in ticket_times if m - pd.Timedelta(days=90) <= t < m)
                f90 = sum(1 for d, failed in failed_hist if failed and m - pd.Timedelta(days=90) <= d < m)
                discount = int(rng.random() < 0.15)
                increase = int(pl == "basic" and m >= PRICE_INCREASE)
                logit = (-3.0 - 0.06 * (sessions - 10) + 0.5 * t90 + 0.9 * f90 - 0.5 * discount
                         + 0.6 * (tenure < 90) + 0.6 * increase - 0.5 * e)
                churned = int(rng.random() < _sigmoid(logit))
                snaps.append({
                    "customer_id": cid, "snapshot_date": m, "plan": pl, "country": country[i],
                    "acquisition_channel": channel[i], "tenure_days": tenure, "monthly_price": price,
                    "sessions_30d": sessions, "avg_session_min": avg_min, "tickets_90d": t90,
                    "failed_payments_90d": f90, "discount_active": discount, "churned_30d": churned,
                    # written AFTER the outcome window by the retention team's tooling:
                    "retention_offer_sent": int(rng.random() < (0.7 if churned else 0.03)),
                })
                if churned:
                    churn_date = m + pd.Timedelta(days=int(rng.integers(1, 30)))
            # --- this month's invoice (dated the 1st); a failed charge may be retried the same day
            failed = rng.random() < 0.06
            status = "failed" if failed else ("refunded" if rng.random() < 0.02 else "paid")
            cust_invoices.append({"customer_id": cid, "invoice_date": m, "amount": price, "status": status})
            failed_hist.append((m, failed))
            if failed and rng.random() < 0.6:
                cust_invoices.append({"customer_id": cid, "invoice_date": m, "amount": price, "status": "paid"})
            # --- support tickets opened during this month
            if m >= pd.Timestamp("2024-10-01"):
                for _ in range(int(rng.poisson(0.12 * np.exp(-0.3 * e)))):
                    opened = m + pd.Timedelta(days=int(rng.integers(0, 28)), minutes=int(rng.integers(0, 1440)))
                    if churn_date is None or opened < churn_date:
                        ticket_times.append(opened)
                        resolved = None if rng.random() < 0.1 else opened + pd.Timedelta(hours=int(rng.integers(1, 96)))
                        tickets.append({"customer_id": cid, "opened_at": opened,
                                        "category": str(rng.choice(["billing", "playback", "account", "other"])),
                                        "resolved_at": resolved})
            if churn_date is not None:
                break
        last_invoice = max(r["invoice_date"] for r in cust_invoices) if cust_invoices else None
        for r in snaps[::-1]:
            if r["customer_id"] != cid:
                break
            # billing-system export column: computed from the FULL invoice history
            r["last_invoice_offset_days"] = (last_invoice - r["snapshot_date"]).days
        invoices.extend(cust_invoices)

    # anonymous tickets (no customer attached) -> NULL customer_id in the tickets table
    for _ in range(60):
        opened = pd.Timestamp("2025-01-01") + pd.Timedelta(minutes=int(rng.integers(0, 365 * 1440)))
        tickets.append({"customer_id": None, "opened_at": opened, "category": "other", "resolved_at": None})

    invoices = pd.DataFrame(invoices).sort_values(["invoice_date", "customer_id"], kind="stable").reset_index(drop=True)
    invoices.insert(0, "invoice_id", np.arange(1, len(invoices) + 1))
    tickets = pd.DataFrame(tickets).sort_values("opened_at", kind="stable").reset_index(drop=True)
    tickets.insert(0, "ticket_id", np.arange(1, len(tickets) + 1))
    export = pd.DataFrame(snaps).sort_values(["snapshot_date", "customer_id"], kind="stable").reset_index(drop=True)
    export["last_invoice_offset_days"] = export["last_invoice_offset_days"].astype(int)

    clean_cols = [c for c in export.columns if c not in ("retention_offer_sent", "last_invoice_offset_days")]
    churn_train = export.loc[export.snapshot_date <= TRAIN_END, clean_cols]
    churn_test = export.loc[export.snapshot_date > TRAIN_END, clean_cols]

    dirty, expected = _dirty_signups(rng, customers, age)
    return {"customers": customers, "invoices": invoices, "tickets": tickets, "export": export,
            "churn_train": churn_train, "churn_test": churn_test, "dirty": dirty, "expected_clean": expected}


def _dirty_signups(rng, customers: pd.DataFrame, age: np.ndarray) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A CRM export with planted defects, plus the ground truth after correct cleaning."""
    rows, truth = [], []
    for i, c in enumerate(customers.itertuples(index=False)):
        d = c.signup_date
        # signup_date: three formats in one column
        u = rng.random()
        if u < 0.60:
            s_date = d.strftime("%Y-%m-%d")
        elif u < 0.85:
            s_date = d.strftime("%d/%m/%Y")
        else:  # local timestamp with UTC offset; the UTC calendar date is the true date
            utc = d + pd.Timedelta(hours=int(rng.integers(0, 24)), minutes=int(rng.integers(0, 60)))
            off = int(rng.choice([-8, -5, 0, 1, 5, 9]))
            local = utc + pd.Timedelta(hours=off)
            s_date = local.strftime("%Y-%m-%dT%H:%M:%S") + f"{'+' if off >= 0 else '-'}{abs(off):02d}:00"
        # country: case / whitespace noise and missing codes
        if pd.isna(c.country):
            s_country, t_country = str(rng.choice(["", "unknown", "-"])), None
        else:
            t_country = c.country
            s_country = str(rng.choice([c.country, c.country.lower(), f" {c.country}", f"{c.country.title()} "],
                                       p=[0.7, 0.1, 0.1, 0.1]))
        # plan: case / whitespace noise, a few invalid values
        if rng.random() < 0.01:
            s_plan, t_plan = "gold", None
        else:
            t_plan = c.plan
            s_plan = str(rng.choice([c.plan, c.plan.title(), f" {c.plan} ", c.plan.upper()], p=[0.7, 0.1, 0.1, 0.1]))
        # price: usd with or without "$", or integer cents flagged by price_unit
        price = PRICES[c.plan]
        u = rng.random()
        if u < 0.6:
            s_price, s_unit = f"{price:.2f}", "usd"
        elif u < 0.8:
            s_price, s_unit = f"${price:.2f}", "usd"
        else:
            s_price, s_unit = str(int(round(price * 100))), "cents"
        # age: missing codes and impossible values
        u = rng.random()
        if u < 0.90:
            s_age, t_age = str(int(age[i])), float(age[i])
        elif u < 0.96:
            s_age, t_age = str(rng.choice(["-1", "999"])), np.nan
        else:
            s_age, t_age = str(rng.choice(["0", "3", "150", "212"])), np.nan
        upd = pd.Timestamp("2025-11-01") + pd.Timedelta(minutes=int(rng.integers(0, 30 * 1440)))
        row = {"customer_id": c.customer_id, "signup_date": s_date, "country": s_country, "plan": s_plan,
               "monthly_price": s_price, "price_unit": s_unit, "age": s_age,
               "updated_at": upd.strftime("%Y-%m-%d %H:%M:%S")}
        rows.append(row)
        truth.append({"customer_id": c.customer_id, "signup_date": d.strftime("%Y-%m-%d"), "country": t_country,
                      "plan": t_plan, "monthly_price_usd": price, "age": t_age})
        u = rng.random()
        if u < 0.03:      # exact duplicate row
            rows.append(dict(row))
        elif u < 0.08:    # stale earlier version of the same customer: different plan, older updated_at
            stale = dict(row)
            other = [p for p in PRICES if p != c.plan]
            stale_plan = str(rng.choice(other))
            stale["plan"] = stale_plan
            stale["monthly_price"], stale["price_unit"] = f"{PRICES[stale_plan]:.2f}", "usd"
            stale["updated_at"] = (upd - pd.Timedelta(days=int(rng.integers(1, 200)))).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(stale)
    dirty = pd.DataFrame(rows).iloc[rng.permutation(len(rows))].reset_index(drop=True)
    return dirty, pd.DataFrame(truth)


# ------------------------------------------------------------------ serialisation
def _csv(df: pd.DataFrame) -> bytes:
    out = df.copy()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            fmt = "%Y-%m-%d" if (out[col].dropna().dt.normalize() == out[col].dropna()).all() else "%Y-%m-%d %H:%M:%S"
            out[col] = out[col].dt.strftime(fmt)
    buf = io.StringIO()
    out.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode()


SCHEMA = """
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY, signup_date TEXT NOT NULL, country TEXT,
    plan TEXT NOT NULL, acquisition_channel TEXT NOT NULL);
CREATE TABLE invoices (
    invoice_id INTEGER PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    invoice_date TEXT NOT NULL, amount REAL NOT NULL, status TEXT NOT NULL);
CREATE TABLE tickets (
    ticket_id INTEGER PRIMARY KEY, customer_id TEXT REFERENCES customers(customer_id),
    opened_at TEXT NOT NULL, category TEXT NOT NULL, resolved_at TEXT);
"""


def _db_rows(data: dict[str, pd.DataFrame]) -> dict[str, list[tuple]]:
    def rows(df: pd.DataFrame, date_fmt: dict[str, str]) -> list[tuple]:
        out = df.copy().astype(object)
        for col, fmt in date_fmt.items():
            out[col] = [None if pd.isna(v) else pd.Timestamp(v).strftime(fmt) for v in df[col]]
        def native(v):  # numpy scalars -> int/float, missing -> None (SQL NULL)
            v = v.item() if hasattr(v, "item") else v
            return None if v is None or (isinstance(v, float) and v != v) or v is pd.NaT else v
        return [tuple(native(v) for v in r) for r in out.itertuples(index=False, name=None)]
    day, sec = "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"
    return {"customers": rows(data["customers"], {"signup_date": day}),
            "invoices": rows(data["invoices"], {"invoice_date": day}),
            "tickets": rows(data["tickets"], {"opened_at": sec, "resolved_at": sec})}


def write_db(path: Path, data: dict[str, pd.DataFrame]) -> None:
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    for table, rows in _db_rows(data).items():
        conn.executemany(f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)
    conn.commit()
    conn.execute("VACUUM")
    conn.close()


def _db_digest_from_file(path: Path) -> str:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    h = hashlib.sha256()
    for table in ("customers", "invoices", "tickets"):
        h.update(repr(conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()).encode())
    conn.close()
    return h.hexdigest()


def _db_digest_from_data(data: dict[str, pd.DataFrame]) -> str:
    h = hashlib.sha256()
    rows = _db_rows(data)
    for table in ("customers", "invoices", "tickets"):
        h.update(repr(sorted(rows[table], key=lambda r: r[0])).encode())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the synthetic StreamBox diagnostic data.")
    ap.add_argument("--check", action="store_true", help="compare regenerated data with the files on disk")
    args = ap.parse_args()
    data = simulate()
    files = {HERE / "signups_dirty.csv": _csv(data["dirty"]),
             HERE / "churn_train.csv": _csv(data["churn_train"]),
             HERE / "churn_test.csv": _csv(data["churn_test"]),
             HERE / "churn_export_full.csv": _csv(data["export"]),
             EXPECTED_CLEAN: _csv(data["expected_clean"])}
    if args.check:
        ok = True
        for path, content in files.items():
            same = path.is_file() and path.read_bytes() == content
            ok &= same
            print(f"{'same     ' if same else 'DIFFERENT'} {path.relative_to(HERE.parent)}")
        same = _db_digest_from_file(HERE / "streambox.db") == _db_digest_from_data(data)
        ok &= same
        print(f"{'same     ' if same else 'DIFFERENT'} data/streambox.db (table contents)")
        return 0 if ok else 1
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        print(f"wrote {path.relative_to(HERE.parent)}  {len(content) / 1e3:.0f} kB")
    write_db(HERE / "streambox.db", data)
    print(f"wrote data/streambox.db  {(HERE / 'streambox.db').stat().st_size / 1e3:.0f} kB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
