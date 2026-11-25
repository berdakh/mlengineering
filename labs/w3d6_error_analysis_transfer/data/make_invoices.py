"""Generate the SYNTHETIC "LedgerLine" invoice table for the w3d6 transfer exercise (part 2).

LedgerLine is an invented B2B software vendor. Every row is simulated. The table exists so that a
complete evaluation can be practised on an unfamiliar business problem whose ground truth is known
to the checks. Nothing found in it is evidence about real customers or real payment behaviour.

    python labs/w3d6_error_analysis_transfer/data/make_invoices.py          # writes invoices.csv
    python labs/w3d6_error_analysis_transfer/data/make_invoices.py --check  # compare with the file

Reading this file before attempting the challenge defeats the leak audit. Read data/README.md instead.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 31706
START, END = "2023-01-01", "2024-12-31"
EXPORT_DATE = pd.Timestamp("2025-03-15")       # the day the table was exported from the billing system
LATE_AFTER_DAYS = 30                            # "late" = paid more than 30 days after the due date
OUT = Path(__file__).parent / "invoices.csv"
SEGMENTS = {"smb": (0.55, 6.6, 0.20), "mid": (0.33, 7.9, -0.05), "enterprise": (0.12, 9.3, -0.30)}
INDUSTRIES = {"retail": 0.15, "construction": 0.35, "software": -0.20, "logistics": 0.10,
              "healthcare": -0.10, "hospitality": 0.25}
COUNTRIES = {"DE": -0.10, "FR": 0.05, "IT": 0.20, "NL": -0.15, "PL": 0.05}
TERMS = {14: -0.15, 30: 0.0, 60: 0.20}


def simulate(seed: int = SEED, n_customers: int = 650, with_truth: bool = False) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start, end = pd.Timestamp(START), pd.Timestamp(END)
    horizon = (end - start).days
    rows = []
    for c in range(n_customers):
        segment = rng.choice(list(SEGMENTS), p=[v[0] for v in SEGMENTS.values()])
        industry = rng.choice(list(INDUSTRIES))
        country = rng.choice(list(COUNTRIES))
        habit = rng.normal(0.0, 1.7)                        # the customer's own payment discipline
        first_day = int(rng.integers(0, horizon - 20)) if rng.random() < 0.55 else int(rng.integers(0, 60))
        monthly_rate = {"smb": 0.6, "mid": 1.0, "enterprise": 1.8}[segment] * rng.lognormal(0, 0.35)
        size = rng.lognormal(0, 0.45)
        terms = int(rng.choice(list(TERMS), p=[0.25, 0.55, 0.20]))
        day = first_day
        while day <= horizon:
            issue = start + pd.Timedelta(days=day)
            amount = float(np.round(np.exp(SEGMENTS[segment][1]) * size * rng.lognormal(0, 0.55), 2))
            downturn = 0.75 * min(max((issue - pd.Timestamp("2024-05-01")).days / 150.0, 0.0), 1.0)
            logit = (-2.3 + habit + SEGMENTS[segment][2] + INDUSTRIES[industry] + COUNTRIES[country]
                     + TERMS[terms] + 0.10 * (np.log(amount) - 7.3) + downturn)
            p = 1.0 / (1.0 + np.exp(-logit))
            late = int(rng.random() < p)
            rows.append((f"C{c + 1:04d}", segment, industry, country, issue, terms, amount, p, late))
            day += int(rng.exponential(30.0 / monthly_rate)) + 1
    df = pd.DataFrame(rows, columns=["customer_id", "segment", "industry", "country", "issue_date",
                                     "payment_terms_days", "amount", "p_true", "late"])
    df["due_date"] = df["issue_date"] + pd.to_timedelta(df["payment_terms_days"], unit="D")
    n = len(df)
    # --- what happened after the due date (not knowable when the invoice is issued) ---------------
    on_time_delay = np.clip(np.round(rng.normal(-2, 9, n)), -25, LATE_AFTER_DAYS).astype(int)
    late_delay = (LATE_AFTER_DAYS + 1 + rng.gamma(2.0, 14.0, n)).astype(int)
    days_after_due = np.where(df["late"] == 1, late_delay, on_time_delay)
    paid_date = df["due_date"] + pd.to_timedelta(days_after_due, unit="D")
    unpaid = paid_date > EXPORT_DATE
    df["days_to_payment"] = np.where(unpaid, np.nan, df["payment_terms_days"] + days_after_due)
    reminder_steps = np.clip(np.floor((days_after_due - 3) / 10.0) + 1, 0, 6)
    df["reminders_sent"] = np.where(days_after_due > 3, reminder_steps + rng.integers(0, 2, n), 0).astype(int)
    df = df.sort_values(["issue_date", "customer_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "invoice_id", np.arange(100001, 100001 + n))
    # --- history that IS knowable at issue time: outcomes resolved before the issue date ----------
    known_date = df["due_date"] + pd.Timedelta(days=LATE_AFTER_DAYS)
    prior_count, prior_resolved, prior_late = np.zeros(n, int), np.zeros(n, int), np.zeros(n, int)
    for _, g in df.groupby("customer_id", sort=False):
        issue, known, late = g["issue_date"].to_numpy(), known_date[g.index].to_numpy(), g["late"].to_numpy()
        for k, i in enumerate(g.index):
            resolved = known[:k] < issue[k]
            prior_count[i], prior_resolved[i] = k, int(resolved.sum())
            prior_late[i] = int(late[:k][resolved].sum())
    df["prior_invoices"] = prior_count
    df["prior_resolved_invoices"] = prior_resolved
    df["prior_late_invoices"] = prior_late
    # --- columns computed at EXPORT time over the customer's whole history -------------------------
    df["customer_late_rate"] = df.groupby("customer_id")["late"].transform("mean").round(3)
    recent = df[df["issue_date"] >= pd.Timestamp("2024-07-01")].groupby("customer_id")["late"].sum()
    df["account_status"] = np.where(df["customer_id"].map(recent).fillna(0) >= 2, "on_hold", "active")
    columns = ["invoice_id", "customer_id", "segment", "industry", "country", "issue_date", "due_date",
               "payment_terms_days", "amount", "prior_invoices", "prior_resolved_invoices",
               "prior_late_invoices", "customer_late_rate", "account_status", "reminders_sent",
               "days_to_payment", "late"]
    if with_truth:
        columns.append("p_true")
    return df[columns]


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n", date_format="%Y-%m-%d")
    return buf.getvalue().encode()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = to_csv_bytes(simulate())
    digest = hashlib.sha256(data).hexdigest()
    if args.check:
        on_disk = hashlib.sha256(OUT.read_bytes()).hexdigest()
        print("regenerated:", digest, "\non disk:    ", on_disk)
        raise SystemExit(0 if digest == on_disk else 1)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data) / 1e6:.2f} MB, sha256 {digest[:16]}...)")


if __name__ == "__main__":
    main()
