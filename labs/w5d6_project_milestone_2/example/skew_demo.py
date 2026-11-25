"""Worked example: training/serving skew from a library default, caught by a parity check.

A demand team normalises daily orders per store: z = (orders - mean of the first n days) / std.
The nightly batch job is written in pandas, the online endpoint in NumPy. Both "compute the std".
pandas' Series.std() defaults to ddof=1 (sample std); numpy.std() defaults to ddof=0 (population std).
SYNTHETIC data; run from the repository root:

    python labs/w5d6_project_milestone_2/example/skew_demo.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def batch_z(history: pd.Series, n: int) -> pd.Series:          # nightly job (pandas)
    base = history.iloc[:n]
    return (history - base.mean()) / base.std()


def online_z(history: np.ndarray, n: int) -> np.ndarray:        # endpoint (NumPy)
    base = history[:n]
    return (history - base.mean()) / base.std()


def parity(n: int, seed: int = 0) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    orders = pd.Series(rng.poisson(120, size=n + 60).astype(float))
    a, b = batch_z(orders, n).to_numpy(), online_z(orders.to_numpy(), n)
    nonzero = a != 0
    return float(np.max(np.abs(a - b))), float(np.median(b[nonzero] / a[nonzero]))


if __name__ == "__main__":
    print(f"{'baseline days n':>15}  {'max |batch - online|':>20}  {'online / batch':>14}  {'sqrt(n/(n-1))':>13}")
    for n in (5, 10, 30, 100, 1000):
        diff, ratio = parity(n)
        print(f"{n:>15}  {diff:>20.4f}  {ratio:>14.4f}  {np.sqrt(n / (n - 1)):>13.4f}")
    print("\nparity check (tolerance 1e-9):", "PASS" if parity(30)[0] <= 1e-9 else "FAIL")
