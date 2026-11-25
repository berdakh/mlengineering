"""Generate the SYNTHETIC card-transaction tables for the w4d2 challenge.

    python labs/w4d2_classical_detectors/challenge/data/make_transactions.py          # writes the CSVs
    python labs/w4d2_classical_detectors/challenge/data/make_transactions.py --check  # compare with files

SYNTHETIC. Each customer has a home location, a typical spend, a card age and usual shopping hours.
A minority of customers are "compromised": part of their transactions are fraudulent (larger, further
from home, at night, online, in bursts). Fraud is about 1-2% of transactions. Only about 5% of the
TRAINING rows carry a label (the rest have label = NaN): labels come from an account review queue that
sees a small random sample of ACCOUNTS and labels every transaction of each reviewed account. The TEST file contains NEW customers, later in time, fully labelled.

Nothing about real payment fraud can be concluded from it. It exists to compare an unsupervised and a
supervised detector under label scarcity, with a customer-grouped structure that punishes row-level
validation.

Columns: tx_id, customer_id, amount, hour, distance_km, merchant_risk, online, n_tx_24h,
card_age_days, label (1 fraud, 0 genuine, NaN unlabelled; train only has NaNs).
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SEED = 20261122
LABEL_FRACTION = 0.05


def simulate(seed: int = SEED, n_customers: int = 1500, first_id: int = 0,
             label_fraction: float | None = LABEL_FRACTION) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for c in range(first_id, first_id + n_customers):
        spend = rng.lognormal(3.5, 0.6)
        card_age = float(rng.uniform(30, 3000))
        usual_hour = rng.uniform(9, 20)
        compromised = rng.random() < 0.10
        n = int(rng.integers(15, 60))
        fraud = np.zeros(n, dtype=int)
        if compromised:
            start = int(rng.integers(0, max(1, n - 8)))
            burst = rng.random(n - start) < 0.5
            fraud[start:][burst] = 1
        for i in range(n):
            f = fraud[i]
            amount = spend * rng.lognormal(0.0, 0.6) * (rng.uniform(1.2, 3.0) if f else 1.0)
            night = rng.random() < (0.35 if f else 0.06)
            hour = (rng.normal(3, 2) if night else rng.normal(usual_hour, 3.0)) % 24
            far = rng.random() < (0.4 if f else 0.05)
            distance = rng.exponential(8.0) + (rng.uniform(50, 1500) if far else 0.0)
            risk = float(np.clip(rng.beta(2, 8) + (0.1 if f else 0.0) * rng.random(), 0, 1))
            online = int(rng.random() < (0.6 if f else 0.35))
            velocity = int(rng.poisson(1.0) + (rng.poisson(1.5) if f else 0))
            rows.append((c, round(amount, 2), round(hour, 2), round(distance, 2), round(risk, 3), online,
                         velocity, round(card_age, 1), f))
    df = pd.DataFrame(rows, columns=["customer_id", "amount", "hour", "distance_km", "merchant_risk",
                                     "online", "n_tx_24h", "card_age_days", "label"])
    df.insert(0, "tx_id", np.arange(len(df)) + first_id * 100)
    df["label"] = df["label"].astype(float)
    if label_fraction is not None:                 # account-level review: whole customers are labelled
        reviewed = rng.random(n_customers) < label_fraction
        hidden = ~reviewed[df["customer_id"].to_numpy() - first_id]
        df.loc[hidden, "label"] = np.nan
    return df


def tables(seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = simulate(seed, n_customers=1500, first_id=0, label_fraction=LABEL_FRACTION)
    test = simulate(seed + 1, n_customers=1000, first_id=100_000, label_fraction=None)
    return train, test


def _bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    train, test = tables()
    ok = True
    for name, df in (("transactions_train.csv", train), ("transactions_test.csv", test)):
        data = _bytes(df)
        if args.check:
            same = hashlib.sha256(data).hexdigest() == hashlib.sha256((HERE / name).read_bytes()).hexdigest()
            print(name, "identical" if same else "DIFFERENT")
            ok &= same
        else:
            (HERE / name).write_bytes(data)
            print(f"wrote {name}: {len(df)} rows, {df['label'].notna().sum()} labelled, "
                  f"{int(df['label'].sum())} labelled frauds")
    raise SystemExit(0 if ok else 1)
