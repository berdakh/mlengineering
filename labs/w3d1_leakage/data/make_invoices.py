"""Generate the SYNTHETIC invoice dataset for the w3d1 leak hunt.

Everything here is simulated. The data exists so that leaks can be planted with known
ground truth; it says nothing about real customers or real payment behaviour.

    python labs/w3d1_leakage/data/make_invoices.py            # writes invoices.csv next to this file
    python labs/w3d1_leakage/data/make_invoices.py --check    # regenerate and compare with the file

Two views of the same simulated world are produced by ``simulate``:

* ``export``     - what the analyst received: an export taken AFTER outcomes were known. Four of its
                   columns contain information that does not exist when an invoice is issued, and
                   some invoices appear twice (re-issues).
* ``production`` - the same kind of rows as the scoring service would see them AT ISSUE TIME, for
                   the months after the export. Used by the checks as ground truth; never shipped.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 31
N_CUSTOMERS = 130
EXPORT_MONTHS = 24          # months 0..23 are in the export
FUTURE_MONTHS = 6           # months 24..29 are the production period
START = pd.Timestamp("2023-01-01")
CUTOFF = pd.Timestamp("2024-09-01")   # month index 20: the last 4 export months form the test period
OUT = Path(__file__).parent / "invoices.csv"

SEGMENTS = ["smb", "mid", "enterprise"]
INDUSTRIES = ["retail", "logistics", "manufacturing", "services", "construction"]
LEAK_COLUMNS = ["reminders_sent", "customer_late_rate", "ledger_ref"]   # + the re-issued rows


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def simulate(seed: int = SEED, n_customers: int = N_CUSTOMERS) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    cust = pd.DataFrame({
        "customer_id": [f"C{i:04d}" for i in range(n_customers)],
        "segment": rng.choice(SEGMENTS, n_customers, p=[0.6, 0.3, 0.1]),
        "industry": rng.choice(INDUSTRIES, n_customers),
        "onboard_month": rng.integers(-36, EXPORT_MONTHS - 4, n_customers),
        "risk": rng.normal(0.0, 1.0, n_customers),                 # latent, never observed
        "rate": rng.gamma(2.5, 1.5, n_customers),                  # invoices per month
    })
    rows = []
    n_months = EXPORT_MONTHS + FUTURE_MONTHS
    for c in cust.itertuples(index=False):
        prior_n, prior_late = 0, 0
        for m in range(max(0, c.onboard_month), n_months):
            k = rng.poisson(c.rate)
            if k == 0:
                continue
            shock = rng.normal(0.0, 1.6)                           # customer-month cash position
            month_rows = []
            for _ in range(k):
                amount = float(np.round(rng.lognormal(7.0, 0.9), 2))
                terms = int(rng.choice([15, 30, 45, 60], p=[0.15, 0.5, 0.2, 0.15]))
                discount = int(rng.random() < 0.25)
                logit = (-2.3 + 0.9 * c.risk + shock + 0.35 * np.log(amount / 1100.0)
                         - 0.012 * (terms - 30) - 0.5 * discount
                         + {"smb": 0.3, "mid": 0.0, "enterprise": -0.4}[c.segment])
                late = int(rng.random() < _sigmoid(logit))
                day = int(rng.integers(0, 28))
                month_rows.append({
                    "customer_id": c.customer_id, "month": m,
                    "issue_date": START + pd.DateOffset(months=m) + pd.Timedelta(days=day),
                    "amount": amount, "payment_terms_days": terms, "discount_offered": discount,
                    "segment": c.segment, "industry": c.industry,
                    "tenure_months": m - c.onboard_month,
                    "n_prior_invoices": prior_n,
                    "prior_late_rate": (prior_late / prior_n) if prior_n else np.nan,
                    "paid_late": late,
                })
            rows.extend(month_rows)                                 # outcomes of a month are known only later
            prior_n += k
            prior_late += sum(r["paid_late"] for r in month_rows)
    df = pd.DataFrame(rows).sort_values(["issue_date", "customer_id"], kind="stable").reset_index(drop=True)
    df.insert(0, "invoice_id", [f"INV{100000 + i}" for i in range(len(df))])
    for j in range(3):                                              # harmless distractors
        df[f"aux_{j}"] = np.round(rng.normal(size=len(df)), 4)

    late = df["paid_late"].to_numpy()
    n = len(df)
    # --- values as they exist AT ISSUE TIME (production view)
    df["reminders_sent"] = 0
    df["ledger_ref"] = 200000 + np.arange(n)
    df["customer_late_rate"] = df["prior_late_rate"]

    export = df[df["month"] < EXPORT_MONTHS].copy()
    production = df[df["month"] >= EXPORT_MONTHS].copy()

    # --- LEAK 1 (target / post-outcome): reminders are sent after the due date passes
    e_late = export["paid_late"].to_numpy()
    export["reminders_sent"] = np.where(e_late == 1, rng.integers(1, 5, len(export)),
                                        (rng.random(len(export)) < 0.04).astype(int))
    # --- LEAK 2 (temporal aggregate): late rate over ALL of the customer's export invoices, incl. this one
    export["customer_late_rate"] = export.groupby("customer_id")["paid_late"].transform("mean").round(4)
    # --- LEAK 3 (shortcut id): invoices sent to collections are re-keyed into a separate ledger range
    rekey = (e_late == 1) & (rng.random(len(export)) < 0.7)
    export.loc[rekey, "ledger_ref"] = 900000 + np.arange(int(rekey.sum()))
    # --- LEAK 4 (near-duplicates): 9% of invoices are re-issued 20-70 days later with a new id,
    #     a slightly corrected amount and THE SAME outcome
    pick = export.sample(frac=0.09, random_state=seed)
    re = pick.copy()
    re["issue_date"] = re["issue_date"] + pd.to_timedelta(rng.integers(20, 71, len(re)), unit="D")
    re = re[re["issue_date"] < START + pd.DateOffset(months=EXPORT_MONTHS)]
    re["amount"] = (re["amount"] * (1 + rng.normal(0, 0.002, len(re)))).round(2)
    re["origin_id"] = re["invoice_id"]
    re["invoice_id"] = [f"INV{500000 + i}" for i in range(len(re))]
    export["origin_id"] = export["invoice_id"]
    export = pd.concat([export, re], ignore_index=True)
    export = export.sort_values(["issue_date", "invoice_id"], kind="stable").reset_index(drop=True)
    production["origin_id"] = production["invoice_id"]
    return export.drop(columns=["month"]), production.drop(columns=["month"])


PUBLIC_COLUMNS = ["invoice_id", "customer_id", "issue_date", "amount", "payment_terms_days",
                  "discount_offered", "segment", "industry", "tenure_months", "n_prior_invoices",
                  "prior_late_rate", "customer_late_rate", "reminders_sent", "ledger_ref",
                  *[f"aux_{j}" for j in range(3)], "paid_late"]


def public_view(frame: pd.DataFrame) -> pd.DataFrame:
    """Drop the ground-truth column ``origin_id``; this is what a learner or a service sees."""
    return frame[PUBLIC_COLUMNS].copy()


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n", date_format="%Y-%m-%d")
    return buf.getvalue().encode()


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the synthetic invoice export.")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    export, _ = simulate()
    data = to_csv_bytes(public_view(export))
    digest = hashlib.sha256(data).hexdigest()
    if args.check:
        same = digest == hashlib.sha256(OUT.read_bytes()).hexdigest()
        print("identical to the committed file" if same else "DIFFERENT from the committed file")
        raise SystemExit(0 if same else 1)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(export)} rows, {len(data) / 1e6:.2f} MB, sha256 {digest[:16]}...)")


if __name__ == "__main__":
    main()
