"""Worked example (SYNTHETIC): why drift p-values and the PSI rule of thumb mislead in monitoring.

    python lessons/w7d2_input_monitoring_drift/example/two_sample_tests.py      # ~5 s

A building's supply-air temperature sensor, sampled once a minute. There is NO drift in parts 1 and 2:
every window comes from the same stationary process. Self-contained (NumPy, SciPy).
"""
from __future__ import annotations

import numpy as np
from scipy import stats

RNG = np.random.default_rng(11)


def ar1(n: int, phi: float, rng) -> np.ndarray:
    """Stationary AR(1) with unit variance: x_t = phi x_{t-1} + e_t."""
    e = rng.normal(0, np.sqrt(1 - phi ** 2), n)
    x = np.empty(n)
    x[0] = rng.normal()
    for i in range(1, n):
        x[i] = phi * x[i - 1] + e[i]
    return x


def psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10, eps: float = 1e-4) -> float:
    edges = np.unique(np.quantile(ref, np.arange(1, bins) / bins))
    p = np.maximum(np.bincount(np.searchsorted(edges, ref, side="right"), minlength=edges.size + 1) / ref.size, eps)
    q = np.maximum(np.bincount(np.searchsorted(edges, cur, side="right"), minlength=edges.size + 1) / cur.size, eps)
    return float(np.sum((q - p) * np.log(q / p)))


def main() -> None:
    print("1) KS test on windows of a stationary process (no drift): share of windows with p < 0.05")
    print("   phi = lag-1 autocorrelation; reference = 2,000 minutes, window = 240 minutes, 400 windows")
    for phi in (0.0, 0.5, 0.9, 0.98):
        hits = 0
        for _ in range(400):
            x = ar1(2240, phi, RNG)
            hits += stats.ks_2samp(x[:2000], x[2000:]).pvalue < 0.05
        print(f"   phi = {phi:4.2f}:  {hits / 400:6.1%}   (nominal 5 %)")

    print("\n2) PSI > 0.1 'moderate shift' rule on windows of i.i.d. data (no drift), reference 5,000")
    ref = RNG.normal(size=5000)
    for n in (30, 60, 240, 1440):
        vals = np.array([psi(ref, RNG.normal(size=n)) for _ in range(1000)])
        print(f"   window n = {n:5d}:  share PSI > 0.1 = {np.mean(vals > 0.1):6.1%}   median PSI = {np.median(vals):.3f}")

    print("\n3) A large sample makes any difference 'significant'")
    a = RNG.normal(20.0, 0.5, 200_000)          # deg C
    b = RNG.normal(20.01, 0.5, 200_000)         # 0.01 deg C warmer: below the sensor's resolution
    res = stats.ks_2samp(a, b)
    print(f"   KS p-value = {res.pvalue:.2g},  W1 = {stats.wasserstein_distance(a, b):.4f} deg C")


if __name__ == "__main__":
    main()
