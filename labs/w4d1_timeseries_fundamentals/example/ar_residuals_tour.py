"""Worked example (SYNTHETIC): autocorrelation, AR fitting, and why the forecaster you choose decides
what kind of anomaly its residuals can see.

    python labs/w4d1_timeseries_fundamentals/example/ar_residuals_tour.py

Uses the REFERENCE flowguard.forecast from solutions/ so that it runs before you have done the lab.
(Point FORECAST_SRC at your own lab/src to run it on your implementation.)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "project" / "get_skab.py").is_file())
SRC = os.environ.get("FORECAST_SRC",
                     str(ROOT / "solutions" / "labs" / "w4d1_timeseries_fundamentals" / "lab" / "src"))
sys.path.insert(0, SRC)

from flowguard.forecast import ARForecaster, NaiveForecaster, acf, cusum, residual_scores  # noqa: E402


def simulate_ar(phi, n, mean=0.0, sigma=1.0, seed=0, burn=500):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n + burn)
    x = np.zeros(n + burn)
    for t in range(len(phi), n + burn):
        x[t] = sum(phi[k] * x[t - 1 - k] for k in range(len(phi))) + e[t]
    return x[burn:] + mean


def pacf_by_regression(x, nlags):
    """Partial autocorrelation at lag k = the last coefficient of an AR(k) fit."""
    return np.array([ARForecaster(k).fit(x).coef_[-1] for k in range(1, nlags + 1)])


def main() -> None:
    # ---- 1. ACF and PACF identify the memory of a process
    x = simulate_ar([0.6, 0.25], 5000, mean=20.0, seed=1)
    print("1. AR(2) with phi = (0.60, 0.25), mean 20, 5000 samples")
    print("   ACF  lags 1-5:", np.round(acf(x, 5)[1:], 2))
    print("   PACF lags 1-5:", np.round(pacf_by_regression(x, 5), 2))

    # ---- 2. effective sample size: how many independent points is a correlated series worth?
    print("\n2. Effective sample size for the mean of an AR(1): n_eff = n (1 - phi) / (1 + phi)")
    for phi in (0.0, 0.5, 0.9):
        means = [simulate_ar([phi], 300, seed=s).mean() for s in range(400)] if phi else \
                [np.random.default_rng(s).standard_normal(300).mean() for s in range(400)]
        var_iid = 1.0 / (1 - phi ** 2) / 300            # what you would assume if rows were independent
        print(f"   phi = {phi:.1f}: Var(mean) simulated {np.var(means):.5f}, i.i.d. formula {var_iid:.5f}, "
              f"n_eff = {300 * (1 - phi) / (1 + phi):.0f} of 300")

    # ---- 3. a level shift seen by three forecasters fitted on the first 300 samples
    y = simulate_ar([0.7], 900, mean=10.0, seed=2)
    y[600:] += 3.0                                     # sustained shift of about 2.1 series SDs (4.2 sigma_e)
    train = y[:300]
    naive, ar1 = NaiveForecaster().fit(train), ARForecaster(1).fit(train)
    s_naive, s_ar = residual_scores(naive, y), residual_scores(ar1, y)
    print("\n3. Level shift of +3.0 at t = 600 (series SD 1.4, innovation SD 1.0)")
    print(f"   AR(1) fitted: phi = {ar1.coef_[0]:.2f}, c = {ar1.intercept_:.2f}, implied mean "
          f"{ar1.intercept_ / (1 - ar1.coef_[0]):.2f}, sigma = {ar1.sigma_:.2f}")
    for name, s in (("naive", s_naive), ("AR(1)", s_ar)):
        print(f"   {name:<6} residual score: before {np.nanmean(s[300:600]):.2f}, "
              f"at the shift {s[600]:.2f}, mean over t = 610-900 {np.mean(s[610:]):.2f}")
    print("   -> the naive residual is a first difference: it sees the step once and then nothing.")
    print("      The AR residual keeps a share (1 - phi) of the offset for as long as it lasts.")

    # ---- 4. CUSUM turns a small persistent offset into an alarm; a per-sample threshold does not
    print("\n4. Small shift of +1.5 at t = 600; the AR(1) residual keeps an offset of about (1 - phi) * 1.5")
    w = simulate_ar([0.7], 1500, mean=10.0, seed=3)
    w[600:] += 1.5
    model = ARForecaster(1).fit(w[:300])
    z = (w - model.predict(w)) / model.sigma_
    def episodes(flag):
        flag = flag.astype(int)
        return int(np.sum(np.diff(np.r_[0, flag]) == 1))
    def first_after(flag, t0=600):
        hit = np.flatnonzero(flag[t0:])
        return int(hit[0]) if len(hit) else None
    print(f"   residual offset after the shift: mean z = {np.mean(z[600:]):.2f} (before: {np.mean(z[300:600]):+.2f})")
    rules = {"|z| > 3 (per sample)": np.abs(np.nan_to_num(z)) > 3.0}
    for k in (0.25, 0.5):
        rules[f"CUSUM k = {k}, h = 5"] = cusum(z, k=k) > 5.0
    for name, flag in rules.items():
        print(f"   {name:<22} alarm episodes in the 300 normal samples before: {episodes(flag[300:600])}; "
              f"first alarm {first_after(flag)} samples after the shift")


if __name__ == "__main__":
    main()
