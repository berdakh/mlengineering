"""Figures for handbook section H7.4 (all SYNTHETIC). Deterministic.

    python handbook/figures/h7_4/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "labs" / "w4d1_timeseries_fundamentals" / "lab" / "src"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.forecast import ARForecaster, acf, cusum  # noqa: E402


def simulate_ar(phi, n, seed=0, burn=500):
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n + burn)
    x = np.zeros(n + burn)
    for t in range(len(phi), n + burn):
        x[t] = sum(phi[k] * x[t - 1 - k] for k in range(len(phi))) + e[t]
    return x[burn:]


def fig_residual_acf():
    x = simulate_ar([0.5, 0.35], 4000, seed=6)
    rows = []
    for p in (1, 2):
        m = ARForecaster(p).fit(x)
        r = acf((x - m.predict(x))[p:], 10)
        rows += [{"model": f"AR({p})", "lag": k, "acf": float(r[k])} for k in range(1, 11)]
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "residual_acf.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    band = 2 / np.sqrt(len(x))
    for ax, (name, d), c in zip(axes, df.groupby("model"), (SERIES[1], SERIES[0])):
        ax.axhspan(-band, band, color=INK["grid"], alpha=0.7, lw=0, zorder=0)
        ax.bar(d["lag"], d["acf"], color=c, width=0.6, zorder=2)
        ax.axhline(0, color=INK["axis"], lw=0.8)
        ax.set_title(f"residuals of {name}", fontsize=10)
        ax.set_xlabel("lag")
    axes[0].set_ylabel("autocorrelation")
    fig.suptitle("SYNTHETIC AR(2) data: an under-fitted AR(1) leaves structure in its residuals",
                 x=0.02, y=1.04, ha="left", fontsize=11, fontweight="bold")
    save(fig, HERE / "residual_acf.svg")


def fig_arl_tradeoff():
    rows = []
    for h in (2.0, 3.0, 4.0, 5.0, 6.0):
        rl0, rl1 = [], []
        for s in range(200):
            z = np.random.default_rng(10_000 + s).standard_normal(6000)
            hit = np.flatnonzero(cusum(z, 0.5) > h)
            rl0.append(hit[0] + 1 if len(hit) else 6000)   # censored at 6000: 6 of 200 runs at h = 6, so its mean is a lower bound
            z1 = np.random.default_rng(20_000 + s).standard_normal(400) + 1.0
            hit = np.flatnonzero(cusum(z1, 0.5) > h)
            rl1.append(hit[0] + 1 if len(hit) else 400)
        rows.append({"h": h, "arl0_mean": float(np.mean(rl0)), "arl1_mean_delta1": float(np.mean(rl1))})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "arl_tradeoff.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(df["arl1_mean_delta1"], df["arl0_mean"], color=SERIES[0], marker="o")
    for _, r in df.iterrows():
        ax.annotate(f"h = {r['h']:g}", (r["arl1_mean_delta1"], r["arl0_mean"]), xytext=(6, -3),
                    textcoords="offset points", fontsize=8, color=INK["secondary"])
    ax.set_yscale("log")
    from matplotlib.ticker import FixedLocator, ScalarFormatter
    ax.yaxis.set_major_locator(FixedLocator([20, 50, 100, 200, 500, 1000, 2000, 5000]))
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_locator(FixedLocator([]))
    ax.set_xlabel("mean delay after a 1-sigma shift (samples)")
    ax.set_ylabel("mean samples between false alarms")
    ax.set_title("Two-sided CUSUM, k = 0.5: every gain in delay is paid in false alarms")
    save(fig, HERE / "arl_tradeoff.svg")


if __name__ == "__main__":
    fig_residual_acf()
    fig_arl_tradeoff()
    print(pd.read_csv(HERE / "arl_tradeoff.csv").round(1).to_string(index=False))
