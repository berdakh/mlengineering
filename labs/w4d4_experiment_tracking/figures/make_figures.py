"""Regenerate every figure of lesson w4d4 (deterministic).

    python labs/w4d4_experiment_tracking/figures/make_figures.py        # a few seconds

Inputs:
* figures/skab_sweep_index.csv - the registry index of the REAL SKAB sweeps (12 runs) built by the
  reference solution on 2026-11-22 (`flowguard sweep` with lab/sweeps/mahalanobis.toml and
  lab/sweeps/iforest.toml, then `flowguard runs table`; data and manifest path columns dropped).
* Figure 2 and the H8.2 figure are SYNTHETIC simulations computed here.
matplotlib is needed only here; the lab and the checks do not import it.
"""
from __future__ import annotations

import statistics
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

MAHAL, IFOREST = SERIES[1], SERIES[3]       # Mahalanobis keeps its w4d3 colour


def fig_sweep() -> None:
    index = pd.read_csv(HERE / "skab_sweep_index.csv")
    rows = []
    for _, r in index.iterrows():
        if r["param.detector.kind"] == "mahalanobis":
            label = f"Mahalanobis  burn-in {int(r['param.detector.burn_in'])}, shrink {r['param.detector.shrinkage']:.1f}"
        else:
            label = f"iforest  burn-in {int(r['param.detector.burn_in'])}, {int(r['param.detector.n_estimators'])} trees"
        rows.append((label, r["param.detector.kind"], r["seed"], r["metric.dev_pooled_pr_auc"]))
    frame = pd.DataFrame(rows, columns=["config", "kind", "seed", "ap"])
    order = (frame.groupby("config")["ap"].mean().sort_values().index.tolist())
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    for y, config in enumerate(order):
        d = frame[frame["config"] == config]
        colour = MAHAL if d["kind"].iloc[0] == "mahalanobis" else IFOREST
        ax.scatter(d["ap"], np.full(len(d), y), color=colour, s=44, zorder=3, edgecolor=INK["surface"], linewidth=1.5)
        if len(d) > 1:
            ax.plot([d["ap"].min(), d["ap"].max()], [y, y], color=colour, linewidth=1.5)
            ax.text(d["ap"].max() + 0.003, y, f"{len(d)} seeds, sd {d['ap'].std(ddof=1):.3f}", va="center",
                    fontsize=8, color=INK["secondary"])
        else:
            ax.text(d["ap"].iloc[0] + 0.003, y, "deterministic (1 run)", va="center", fontsize=8,
                    color=INK["secondary"])
    ax.set_yticks(range(len(order)), order, fontsize=8.5)
    ax.set_xlabel("pooled PR-AUC on the 27 development experiments (rows t >= 200)")
    ax.set_xlim(0.6, 0.79)
    ax.set_title("12 registered runs: burn-in length matters more than shrinkage or tree count")
    save(fig, HERE / "sweep_results.svg")
    print(frame.groupby("config")["ap"].agg(["count", "mean", "std"]).round(4).to_string())


def sd_estimate_quantiles(true_sd: float = 0.02, ns=(2, 3, 5, 10, 20), reps: int = 20000, seed: int = 0):
    rng = np.random.default_rng(seed)
    out = []
    for n in ns:
        est = [statistics.stdev(rng.normal(0.8, true_sd, size=n)) for _ in range(reps)]
        out.append((n, *np.percentile(est, [10, 50, 90])))
    return out


def fig_sd_estimate(path: Path) -> None:
    q = sd_estimate_quantiles()
    ns = [r[0] for r in q]
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.axhline(0.02, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(ns[-1], 0.0207, "true seed sd 0.020", ha="right", fontsize=8, color=INK["muted"])
    ax.fill_between(ns, [r[1] for r in q], [r[3] for r in q], color=SERIES[0], alpha=0.18, linewidth=0,
                    label="10th-90th percentile of the estimate")
    ax.plot(ns, [r[2] for r in q], marker="o", color=SERIES[0], label="median estimate")
    ax.set_xscale("log")
    ax.set_xticks(ns, [str(n) for n in ns])
    ax.minorticks_off()
    ax.set_xlabel("number of seeds")
    ax.set_ylabel("estimated sd over seeds")
    ax.legend(loc="upper right")
    ax.set_title("With 3 seeds the estimated spread can be a third or 1.5x the truth (SYNTHETIC)")
    save(fig, path)
    for n, lo, med, hi in q:
        print(f"n={n}: median {med:.4f}, 10-90% {lo:.4f}-{hi:.4f}")


if __name__ == "__main__":
    fig_sweep()
    fig_sd_estimate(HERE / "sd_estimate.svg")
    fig_sd_estimate(ROOT / "docs" / "handbook" / "ch08_reproducible_experiments" / "figures" / "h8_2_sd_estimate.svg")
