"""Worked example (SYNTHETIC data): what a centred window does to a detector, and the delay/noise tradeoff.

    python labs/w2d5_feature_pipeline/example/lookahead_demo.py

The series is simulated: Gaussian noise (white, or AR(1) with coefficient 0.9) plus a step of
height DELTA at a known onset. It demonstrates mechanics. It says nothing about real equipment.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

N, ONSET, DELTA, SIGMA = 600, 300, 2.0, 0.5
WINDOWS = (10, 30, 60)
N_REPEATS = 400


def simulate(rng: np.random.Generator, phi: float = 0.0) -> np.ndarray:
    """Noise with standard deviation SIGMA (AR(1) if phi > 0) plus a step of DELTA from ONSET on."""
    eps = rng.normal(0.0, SIGMA * np.sqrt(1 - phi**2), N)
    noise = np.empty(N)
    noise[0] = rng.normal(0.0, SIGMA)
    for i in range(1, N):
        noise[i] = phi * noise[i - 1] + eps[i]
    return noise + DELTA * (np.arange(N) >= ONSET)


def first_crossing(score: pd.Series, threshold: float) -> float:
    """Delay in samples from ONSET to the first threshold crossing at or after ONSET - 60."""
    hits = np.flatnonzero((score.to_numpy() > threshold) & (np.arange(N) >= ONSET - 60))
    return float(hits[0] - ONSET) if len(hits) else np.nan


def main() -> None:
    rng = np.random.default_rng(0)
    theta = 0.25 * DELTA  # alert when the rolling mean has moved a quarter of the way to the new level

    print("1) Detection delay of a rolling mean, threshold = DELTA/4, white noise, median over "
          f"{N_REPEATS} simulated series")
    print(f"{'w':>4} {'predicted w*theta/DELTA':>24} {'causal':>8} {'centred':>8}")
    for w in WINDOWS:
        causal, centred = [], []
        for _ in range(N_REPEATS):
            x = pd.Series(simulate(rng))
            causal.append(first_crossing(x.rolling(w, min_periods=w).mean(), theta))
            centred.append(first_crossing(x.rolling(w, min_periods=w, center=True).mean(), theta))
        print(f"{w:>4} {w * theta / DELTA:>24.1f} {np.nanmedian(causal):>8.1f} {np.nanmedian(centred):>8.1f}")
    print("   A negative delay means the alert fires BEFORE the fault begins: the feature has read the future.\n")

    print("2) Standard deviation of the rolling mean on fault-free noise (unit-variance input)")
    print(f"{'w':>4} {'1/sqrt(w)':>10} {'white':>8} {'AR(1) phi=0.9':>14} {'effective n (AR)':>17}")
    long_rng = np.random.default_rng(1)
    for w in WINDOWS:
        sd = {}
        for phi in (0.0, 0.9):
            eps = long_rng.normal(0.0, np.sqrt(1 - phi**2), 200_000)
            x = np.empty_like(eps)
            x[0] = long_rng.normal()
            for i in range(1, len(x)):
                x[i] = phi * x[i - 1] + eps[i]
            sd[phi] = pd.Series(x).rolling(w).mean().std()
        print(f"{w:>4} {1 / np.sqrt(w):>10.3f} {sd[0.0]:>8.3f} {sd[0.9]:>14.3f} {1 / sd[0.9] ** 2:>17.1f}")
    print("   Under positive autocorrelation a window of w samples carries far fewer than w independent ones.\n")

    print("3) False alerts per 1000 fault-free samples at threshold DELTA/4 (white noise)")
    for w in WINDOWS:
        x = pd.Series(np.random.default_rng(2).normal(0, SIGMA, 200_000))
        rate = 1000 * (x.rolling(w).mean() > theta).mean()
        print(f"   w={w:>3}: {rate:7.2f}")


if __name__ == "__main__":
    main()
