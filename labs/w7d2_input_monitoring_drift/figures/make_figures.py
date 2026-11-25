"""Regenerate the w7d2 figures (deterministic).

    python labs/w7d2_input_monitoring_drift/figures/make_figures.py

Figures 1-2 use REAL SKAB data through the reference solution's ``replay_drift.py`` (run here if its
results are missing; needs ``python project/get_skab.py``). Figures 3-4 are SYNTHETIC (the worked
example's processes). Numbers are printed and written to figure_data.csv.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "example"))

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

SOL_LAB = ROOT / "solutions" / "labs" / "w7d2_input_monitoring_drift" / "lab"
ROWS: list[dict] = []


def replay() -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    res = SOL_LAB / "results"
    if not (res / "windows_global.csv").is_file():
        subprocess.run([sys.executable, str(SOL_LAB / "replay_drift.py")], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)
    return (pd.read_csv(res / "windows_global.csv"), pd.read_csv(res / "windows_per_run.csv"),
            json.loads((res / "summary.json").read_text()))


def fig_timelines(a: pd.DataFrame, b: pd.DataFrame) -> None:
    exps = ["valve1/13", "other/14"]
    fig, axes = plt.subplots(len(exps), 1, figsize=(8.0, 4.6), sharey=True)
    for ax, exp in zip(axes, exps):
        for df, name, colour in ((a, "A: global reference", SERIES[0]), (b, "B: per-run reference", SERIES[1])):
            sub = df[df["experiment"] == exp].sort_values("start")
            ax.plot(sub["start"] / 60, sub["max_ratio"], "o-", color=colour, label=name, markersize=5, lw=1.6)
            for r in sub.itertuples():
                ROWS.append({"figure": "timeline", "series": f"{exp} {name[:1]}", "x": r.start, "y": round(r.max_ratio, 3)})
        for r in a[a["experiment"] == exp].itertuples():
            if r.label == "anomalous":
                ax.axvspan(r.start / 60, r.start / 60 + 1, color=STATUS["warning"], alpha=0.18, lw=0)
        ax.axhline(1.0, color=INK["muted"], ls="--", lw=1)
        ax.set_yscale("log")
        ax.set_yticks([0.25, 0.5, 1, 2, 4, 8], ["0.25", "0.5", "1", "2", "4", "8"])
        ax.minorticks_off()
        ax.set_title(f"{exp}: largest statistic / threshold over the 8 sensors (shaded: labelled fault)", fontsize=10)
        ax.set_ylabel("ratio (log)")
    axes[-1].set_xlabel("minutes since the start of the run (first 5 minutes = burn-in, not monitored)")
    axes[0].legend(loc="upper left", fontsize=8)
    axes[0].text(axes[0].get_xlim()[1], 1.1, "alert above 1", ha="right", color=INK["secondary"], fontsize=8)
    fig.tight_layout()
    save(fig, HERE / "drift_timelines.svg")


def fig_rates(summary: list[dict]) -> None:
    test = [s for s in summary if "(test)" in s["reference"]]
    groups = [("normal windows", "normal_alert_rate"), ("anomalous windows", "anomalous_alert_rate"),
              ("normal, valve families", None), ("normal, other family", "normal_alert_rate_other")]
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    width = 0.38
    for i, s in enumerate(test):
        vals = [s["normal_alert_rate"], s["anomalous_alert_rate"],
                max(s["normal_alert_rate_valve1"], s["normal_alert_rate_valve2"]), s["normal_alert_rate_other"]]
        xs = np.arange(len(vals)) + (i - 0.5) * width
        ax.bar(xs, vals, width=width * 0.92, color=SERIES[i], label=s["reference"].replace(" (test)", ""))
        for x, v in zip(xs, vals):
            ax.text(x, v + 0.02, f"{v:.0%}", ha="center", fontsize=8, color=INK["secondary"])
            ROWS.append({"figure": "rates", "series": s["reference"], "x": round(float(x), 2), "y": v})
    ax.set_xticks(range(len(groups)), [g for g, _ in groups])
    ax.set_ylabel("share of windows with an alert")
    ax.set_ylim(0, 1.12)
    ax.axhline(0.05, color=INK["muted"], ls="--", lw=1)
    ax.text(1.5, 0.07, "target 5 %", ha="center", fontsize=8, color=INK["secondary"])
    ax.set_title("Real SKAB test runs: the drift monitor mostly misses faults and its false alarms depend on the reference")
    ax.title.set_fontsize(10)
    ax.legend(loc="upper left", fontsize=8)
    save(fig, HERE / "alert_rates.svg")


def fig_ks_autocorrelation() -> None:
    import two_sample_tests as ex
    rng = np.random.default_rng(11)
    phis = [0.0, 0.25, 0.5, 0.75, 0.9, 0.98]
    rates = []
    for phi in phis:
        hits = 0
        for _ in range(300):
            x = ex.ar1(2240, phi, rng)
            hits += stats.ks_2samp(x[:2000], x[2000:]).pvalue < 0.05
        rates.append(hits / 300)
        ROWS.append({"figure": "ks_autocorrelation", "series": "share p<0.05", "x": phi, "y": hits / 300})
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.plot(phis, rates, "o-", color=SERIES[0])
    ax.axhline(0.05, color=INK["muted"], ls="--", lw=1)
    ax.text(0.0, 0.09, "nominal 5 %", fontsize=8, color=INK["secondary"])
    ax.set_xlabel("lag-1 autocorrelation of the sensor (phi)")
    ax.set_ylabel("windows with KS p < 0.05")
    ax.set_ylim(0, 1.05)
    ax.set_title("No drift at all, yet the KS test 'detects' it (SYNTHETIC)")
    save(fig, HERE / "ks_autocorrelation.svg")


def fig_psi_window() -> None:
    import two_sample_tests as ex
    rng = np.random.default_rng(12)
    ref = rng.normal(size=5000)
    ns = [30, 60, 120, 240, 480, 1440]
    shares = []
    for n in ns:
        vals = np.array([ex.psi(ref, rng.normal(size=n)) for _ in range(600)])
        shares.append(float(np.mean(vals > 0.1)))
        ROWS.append({"figure": "psi_window", "series": "share PSI>0.1", "x": n, "y": shares[-1]})
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.plot(ns, shares, "o-", color=SERIES[1])
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.set_xlabel("window size (samples)")
    ax.set_ylabel("stable windows with PSI > 0.1")
    ax.set_ylim(0, 1.05)
    ax.set_title("The PSI > 0.1 rule's false-alarm rate depends on the window size (SYNTHETIC)")
    ax.title.set_fontsize(10)
    save(fig, HERE / "psi_window_size.svg")


def main() -> None:
    apply()
    a, b, summary = replay()
    fig_timelines(a, b)
    fig_rates(summary)
    fig_ks_autocorrelation()
    fig_psi_window()
    with (HERE / "figure_data.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
        w.writeheader()
        w.writerows(ROWS)
    for r in ROWS:
        if r["figure"] in ("ks_autocorrelation", "psi_window", "rates"):
            print(r)


if __name__ == "__main__":
    main()
