"""Regenerate every figure of lesson w4d1. Deterministic.

    python project/get_skab.py                                            # once (real-data figures)
    python labs/w4d1_timeseries_fundamentals/figures/make_figures.py

Writes figures/*.svg and figures/*.csv (the plotted numbers). Uses the REFERENCE package in
solutions/ so the figures do not depend on the state of your lab.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
REF = ROOT / "solutions" / "labs" / "w4d1_timeseries_fundamentals" / "lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REF / "src"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.data import load_raw  # noqa: E402
from flowguard.forecast import ARForecaster, NaiveForecaster, acf, cusum, residual_scores  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

BURN_IN = 100


def simulate_ar(phi, n, mean=0.0, sigma=1.0, seed=0, burn=500):
    rng = np.random.default_rng(seed)
    e = rng.normal(0.0, sigma, n + burn)
    x = np.zeros(n + burn)
    for t in range(len(phi), n + burn):
        x[t] = sum(phi[k] * x[t - 1 - k] for k in range(len(phi))) + e[t]
    return x[burn:] + mean


def shade(ax, anomaly, t):
    on = np.flatnonzero(np.diff(np.r_[0, anomaly, 0]) == 1)
    off = np.flatnonzero(np.diff(np.r_[0, anomaly, 0]) == -1)
    for a, b in zip(on, off):
        ax.axvspan(t[a], t[b - 1], color=SERIES[1], alpha=0.12, lw=0)


def fig_acf(tidy, manifest):
    sensors = ["thermocouple", "temperature", "current", "flow_rate"]
    burn = tidy[tidy["experiment_id"].isin(dev_experiments(manifest)) & (tidy["t"] < BURN_IN)]
    rows = []
    for sensor in sensors:
        r = np.array([acf(g.sort_values("t")[sensor].to_numpy(float), 20)
                      for _, g in burn.groupby("experiment_id") if g[sensor].std() > 0])
        med = np.median(r, axis=0)
        rows += [{"sensor": sensor, "lag": k, "median_acf": float(med[k])} for k in range(21)]
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "acf_sensors.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for i, sensor in enumerate(sensors):
        d = df[df["sensor"] == sensor]
        ax.plot(d["lag"], d["median_acf"], color=SERIES[i], marker="o", markersize=3, label=sensor)
    ax.axhline(0, color=INK["axis"], lw=0.8)
    band = 2 / np.sqrt(BURN_IN)
    ax.axhspan(-band, band, color=INK["grid"], alpha=0.6, lw=0)
    ax.text(20, -band, "band: +/- 2 / sqrt(100), the noise level of one 100-sample estimate", ha="right", va="bottom", fontsize=8,
            color=INK["secondary"])
    ax.set_xlim(0, 20.5)
    ax.set_xlabel("lag (samples, about 1 s each)")
    ax.set_ylabel("autocorrelation (median over 27 experiments)")
    ax.set_title("Temperatures remember the last 20 s; flow rate barely remembers 1 s")
    ax.legend(loc="upper right")
    save(fig, HERE / "acf_sensors.svg")


def fig_level_shift():
    y = simulate_ar([0.7], 900, mean=10.0, seed=2)
    y[600:] += 3.0
    naive, ar1 = NaiveForecaster().fit(y[:300]), ARForecaster(1).fit(y[:300])
    s_n, s_a = residual_scores(naive, y), residual_scores(ar1, y)
    t = np.arange(len(y))
    pd.DataFrame({"t": t, "y": y, "naive_score": s_n, "ar1_score": s_a}).to_csv(HERE / "level_shift.csv", index=False)
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.4), sharex=True)
    axes[0].plot(t, y, color=INK["secondary"], lw=1.0)
    axes[0].axvspan(0, 300, color=INK["grid"], alpha=0.7, lw=0)
    axes[0].text(150, y.max(), "fit window", ha="center", va="top", fontsize=8, color=INK["secondary"])
    axes[0].set_ylabel("value")
    axes[0].set_title("SYNTHETIC AR(1) with a +3 level shift at t = 600: what each residual sees")
    for ax, s, name, c in ((axes[1], s_n, "naive residual score", SERIES[0]),
                           (axes[2], s_a, "AR(1) residual score", SERIES[2])):
        ax.plot(t, s, color=c, lw=0.9)
        roll = pd.Series(s).rolling(50, min_periods=10).mean()
        ax.plot(t, roll, color=INK["primary"], lw=1.6, label="50-sample mean")
        ax.set_ylabel(name, fontsize=8)
        ax.set_ylim(0, 5)
    axes[1].legend(loc="upper left")
    for ax in axes:
        ax.axvline(600, color=INK["muted"], lw=0.8, ls=":", zorder=0)
    axes[2].set_xlabel("sample")
    save(fig, HERE / "level_shift_residuals.svg")


def fig_skab_experiment(tidy):
    e = "valve1/0"
    g = tidy[tidy["experiment_id"] == e].sort_values("t")
    x = g["flow_rate"].to_numpy(float)
    t = g["t"].to_numpy()
    model = ARForecaster(2).fit(x[:BURN_IN])
    pred = model.predict(x)
    z = (x - pred) / model.sigma_
    stat = cusum(np.clip(z, -50, 50), k=0.5)
    a = g["anomaly"].to_numpy()
    pd.DataFrame({"t": t, "flow_rate": x, "ar2_forecast": pred, "z": z, "cusum": stat, "anomaly": a}).to_csv(
        HERE / "skab_valve1_0.csv", index=False)
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 5.6), sharex=True)
    axes[0].plot(t, x, color=INK["secondary"], lw=0.9, label="flow rate")
    axes[0].plot(t, pred, color=SERIES[0], lw=0.9, alpha=0.8, label="AR(2) one-step forecast")
    axes[0].axvspan(0, BURN_IN, color=INK["grid"], alpha=0.7, lw=0)
    axes[0].set_ylabel("L/min")
    axes[0].legend(loc="lower left", fontsize=8)
    axes[0].set_title(f"Real SKAB {e} (development): forecast, residual and CUSUM; labelled fault shaded")
    axes[1].plot(t, np.abs(z), color=SERIES[2], lw=0.8)
    axes[1].set_ylabel("|z| residual", fontsize=8)
    axes[1].set_ylim(0, min(30, np.nanmax(np.abs(z)) * 1.05))
    axes[2].plot(t, stat, color=SERIES[6], lw=1.2)
    axes[2].axhline(5, color=INK["muted"], lw=0.8, ls="--")
    axes[2].text(t[-1], 5, " h = 5", va="bottom", ha="right", fontsize=8, color=INK["secondary"])
    axes[2].set_ylabel("CUSUM statistic", fontsize=8)
    axes[2].set_xlabel("row t (about 1 s)")
    for ax in axes:
        shade(ax, a, t)
    save(fig, HERE / "skab_valve1_0.svg")


def fig_test_comparison(tidy, manifest):
    out = HERE / "test_comparison.json"
    subprocess.run([sys.executable, str(REF / "forecast_vs_z.py"), "--json", str(out)], check=True,
                   stdout=subprocess.DEVNULL)
    res = json.loads(out.read_text())
    rows = pd.DataFrame(res["rows"])
    rows.to_csv(HERE / "test_comparison.csv", index=False)
    out.unlink()
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    order = rows.index[::-1]
    for pos, i in enumerate(order):
        r = rows.loc[i]
        ax.plot([r["low"], r["high"]], [pos, pos], color=SERIES[0], lw=2, solid_capstyle="round")
        ax.plot(r["pr_auc"], pos, "o", color=SERIES[0], markersize=7, markeredgecolor=INK["surface"], mew=1.5)
        ax.text(r["high"] + 0.01, pos, f"{r['pr_auc']:.3f}", va="center", fontsize=8, color=INK["secondary"])
    test_rows = tidy[tidy["experiment_id"].isin(manifest["test"]) & (tidy["t"] >= BURN_IN)]
    prevalence = float(test_rows["anomaly"].mean())
    ax.axvline(prevalence, color=INK["muted"], lw=1.0, ls="--")
    ax.text(prevalence, len(rows) - 0.55, f" no-skill floor = prevalence {prevalence:.3f}", fontsize=8,
            color=INK["secondary"], va="bottom")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows.loc[order, "detector"], fontsize=8)
    ax.set_xlim(0.3, 1.0)
    ax.set_ylim(-0.6, len(rows) - 0.1)
    ax.set_xlabel("test PR-AUC, point level (95% cluster-bootstrap interval, 7 experiments)")
    ax.set_title("On SKAB the naive residual is at the no-skill floor; AR(2) lands between the two z-scores")
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "test_comparison.svg")


def fig_cusum_delay():
    rows = []
    for delta in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0):
        delays = []
        for seed in range(300):
            z = np.random.default_rng(seed).standard_normal(400)
            z[100:] += delta
            hit = np.flatnonzero(cusum(z, k=0.5)[100:] > 5.0)
            delays.append(hit[0] + 1 if len(hit) else np.nan)
        rows.append({"shift_sigma": delta, "median_delay": float(np.nanmedian(delays)),
                     "approx_h_over_delta_minus_k": 5.0 / (delta - 0.5) if delta > 0.5 else np.nan})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "cusum_delay.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(df["shift_sigma"], df["median_delay"], color=SERIES[0], marker="o", label="simulated (300 runs)")
    ax.plot(df["shift_sigma"], df["approx_h_over_delta_minus_k"], color=SERIES[1], ls="--", label="h / (delta - k)")
    ax.set_yscale("log")
    from matplotlib.ticker import FixedLocator, ScalarFormatter
    ax.yaxis.set_major_locator(FixedLocator([2, 3, 5, 10, 20, 30]))
    ax.yaxis.set_major_formatter(ScalarFormatter())
    ax.yaxis.set_minor_locator(FixedLocator([]))
    ax.set_xlabel("shift delta (in residual standard deviations)")
    ax.set_ylabel("median samples to alarm")
    ax.set_title("CUSUM (k = 0.5, h = 5): a shift equal to k already needs about 27 samples")
    ax.legend()
    save(fig, HERE / "cusum_delay.svg")


def main() -> None:
    fig_level_shift()
    fig_cusum_delay()
    try:
        tidy = load_raw(ROOT / "data" / "raw" / "skab")
    except FileNotFoundError as exc:
        print(f"skipping real-data figures: {exc}")
        return
    manifest = load_splits(REF / "splits" / "v2.json")
    fig_acf(tidy, manifest)
    fig_skab_experiment(tidy)
    fig_test_comparison(tidy, manifest)
    print("figures written to", HERE)


if __name__ == "__main__":
    main()
