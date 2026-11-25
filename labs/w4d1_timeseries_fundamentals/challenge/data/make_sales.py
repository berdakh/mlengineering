"""Generate the SYNTHETIC store-sales table for the w4d1 challenge.

    python labs/w4d1_timeseries_fundamentals/challenge/data/make_sales.py          # writes sales.csv
    python labs/w4d1_timeseries_fundamentals/challenge/data/make_sales.py --check  # compare with file

SYNTHETIC: daily unit sales for 10 stores over two years, with a weekly pattern, slow drift,
autocorrelated noise, labelled promotion periods (3-6 days, +40% to +80%) and, in three stores, an
UNLABELLED permanent level increase (a new product line) part-way through. Nothing about real retail
can be concluded from it; it exists to exercise forecast-residual detection with seasonality.

Columns: date (YYYY-MM-DD), store (S01..S10), sales (float, units), promo (1 on promotion days).
"""
from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent / "sales.csv"
SEED = 20261122
START = "2024-01-01"
DAYS = 730
DEV_END = "2025-07-01"          # development period: dates before this; test: on or after


def simulate(seed: int = SEED, n_stores: int = 10, days: int = DAYS) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range(START, periods=days, freq="D")
    dow = dates.dayofweek.to_numpy()
    frames = []
    shift_stores = set(rng.choice(n_stores, size=3, replace=False).tolist())
    for s in range(n_stores):
        level = rng.uniform(60, 200)
        weekly = np.array([0.85, 0.80, 0.85, 0.95, 1.10, 1.35, 1.20]) * rng.uniform(0.95, 1.05, 7)
        drift = np.cumsum(rng.normal(0, 0.002, days))
        noise = np.zeros(days)
        e = rng.normal(0, 0.07, days)
        for t in range(1, days):
            noise[t] = 0.5 * noise[t - 1] + e[t]
        log_sales = np.log(level) + np.log(weekly[dow]) + drift + noise
        if s in shift_stores:                       # unlabelled benign level change
            at = int(rng.integers(200, days - 150))
            log_sales[at:] += np.log(rng.uniform(1.25, 1.4))
        promo = np.zeros(days, dtype=int)
        n_promos = int(rng.integers(8, 13))
        for start in sorted(rng.choice(np.arange(30, days - 10), size=n_promos, replace=False)):
            length = int(rng.integers(3, 7))
            if promo[max(0, start - 10):start + length + 10].any():
                continue                            # keep promotions apart
            promo[start:start + length] = 1
            log_sales[start:start + length] += np.log(rng.uniform(1.4, 1.8))
        frames.append(pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "store": f"S{s + 1:02d}",
                                    "sales": np.round(np.exp(log_sales), 2), "promo": promo}))
    return pd.concat(frames, ignore_index=True)


def to_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False, lineterminator="\n")
    return buf.getvalue().encode()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = to_bytes(simulate())
    if args.check:
        same = hashlib.sha256(data).hexdigest() == hashlib.sha256(OUT.read_bytes()).hexdigest()
        print("identical" if same else "DIFFERENT")
        raise SystemExit(0 if same else 1)
    OUT.write_bytes(data)
    print(f"wrote {OUT} ({len(data) / 1e3:.0f} kB)")
