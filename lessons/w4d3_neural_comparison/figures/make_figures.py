"""Regenerate every figure of lesson w4d3 (deterministic given its inputs).

    python lessons/w4d3_neural_comparison/figures/make_figures.py        # a few seconds

Inputs:
* figures/neural_vs_classical.json - REAL SKAB results written by lab/compare_seeds.py (reference
  solution, 2026-11-22, one CPU thread). Regenerate it with
  `python solutions/lessons/w4d3_neural_comparison/lab/compare_seeds.py --out lessons/w4d3_neural_comparison/figures/neural_vs_classical.json`.
* example/seed_lottery.json - SYNTHETIC results written by example/seed_lottery.py.
Also writes the handbook figure for H7.6 (best-of-k optimism). The plotted numbers are printed.
matplotlib is needed only here; the lab and the checks do not import it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = UNIT.parents[1]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

NEURAL, MAHAL, FLOW = SERIES[0], SERIES[1], SERIES[2]   # fixed colour per detector across all figures
real = json.loads((HERE / "neural_vs_classical.json").read_text())
synthetic = json.loads((UNIT / "example" / "seed_lottery.json").read_text())


def fig_seed_spread() -> None:
    seeds = real["neural_seeds"]
    test = real["test"]
    names = list(test)
    neural_name = next(n for n in names if n.startswith("neural"))
    mahal_name = next(n for n in names if n.startswith("Mahalanobis"))
    flow_name = next(n for n in names if n.startswith("flow_rate"))
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    rows = [("neural AE, 5 seeds", NEURAL), ("Mahalanobis burn-in", MAHAL), ("flow_rate |z| burn-in", FLOW)]
    for y, (label, colour) in enumerate(rows):
        ax.text(-0.01, y, label, ha="right", va="center", transform=ax.get_yaxis_transform(), fontsize=9,
                color=INK["primary"])
    values = [r["test_pr_auc"] for r in seeds]
    ax.scatter(values, np.zeros(len(values)), s=46, color=NEURAL, zorder=3, edgecolor=INK["surface"], linewidth=1.5)
    for r in seeds:
        ax.annotate(f"s{r['seed']}", (r["test_pr_auc"], 0), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, color=INK["secondary"])
    ci = test[neural_name]
    ax.plot([ci["low"], ci["high"]], [-0.22, -0.22], color=NEURAL, linewidth=2)
    ax.text(ci["high"] + 0.005, -0.22, f"95% CI, seed {neural_name.split('seed ')[1].split(',')[0]} only",
            va="center", fontsize=8, color=INK["secondary"])
    for y, name, colour in ((1, mahal_name, MAHAL), (2, flow_name, FLOW)):
        c = test[name]
        ax.plot([c["low"], c["high"]], [y, y], color=colour, linewidth=2)
        ax.scatter([c["estimate"]], [y], s=46, color=colour, zorder=3, edgecolor=INK["surface"], linewidth=1.5)
        ax.annotate(f"{c['estimate']:.3f}", (c["estimate"], y), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, color=INK["secondary"])
    ax.set_yticks([])
    ax.set_ylim(-0.6, 2.6)
    ax.set_xlim(0.5, 1.0)
    ax.set_xlabel("pooled point-level PR-AUC on the 7 test experiments (rows t >= 100)")
    ax.set_title("Seed spread of the autoencoder spans most of the gap to Mahalanobis; flow-rate z beats both")
    ax.spines["left"].set_visible(False)
    save(fig, HERE / "seed_spread.svg")
    print("seed_spread:", [round(v, 3) for v in values], {n: round(test[n]["estimate"], 3) for n in names})


def fig_learning_curves() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.4), sharey=True)
    for i, r in enumerate(real["neural_seeds"]):
        colour = SERIES[i]
        epochs = np.arange(len(r["val_loss"]))
        axes[0].plot(epochs, r["train_loss"], color=colour, linewidth=1.6)
        axes[1].plot(epochs, r["val_loss"], color=colour, linewidth=1.6, label=f"seed {r['seed']}")
        axes[1].scatter([r["best_epoch"]], [r["val_loss"][r["best_epoch"]]], color=colour, s=40, zorder=3,
                        edgecolor=INK["surface"], linewidth=1.5)
    axes[0].set_title("FIT loss", fontweight="normal", fontsize=10)
    axes[1].set_title("VAL loss (dot = restored epoch)", fontweight="normal", fontsize=10)
    for ax in axes:
        ax.set_xlabel("epoch")
    axes[0].set_ylabel("mean squared reconstruction error")
    axes[1].legend(loc="upper right", ncol=1, fontsize=8)
    lowest = min(real["neural_seeds"], key=lambda r: min(r["val_loss"]))
    title = (f"Seed {lowest['seed']} reaches the lowest VAL loss and has the lowest TEST PR-AUC "
             f"({lowest['test_pr_auc']:.3f}): reconstruction loss is not the detection metric")
    fig.suptitle(title, x=0.01, y=1.04, ha="left", fontweight="bold", fontsize=10.5)
    save(fig, HERE / "learning_curves.svg")
    print("best epochs:", [(r["seed"], r["best_epoch"], r["stopped_epoch"]) for r in real["neural_seeds"]])


def fig_tuning() -> None:
    neural = real["tuning"]["neural"]
    classical = real["tuning"]["classical"]
    fig, axes = plt.subplots(1, 2, figsize=(8.6, 3.0), sharey=True)
    labels = [f"w{t['window']} b{t['bottleneck']}" for t in neural]
    axes[0].bar(labels, [t["val_pr_auc"] for t in neural], color=NEURAL, width=0.6)
    axes[1].bar([f"shrink {t['shrinkage']:.1f}" for t in classical], [t["val_pr_auc"] for t in classical],
                color=MAHAL, width=0.6)
    for ax, trials in ((axes[0], neural), (axes[1], classical)):
        for i, t in enumerate(trials):
            ax.text(i, t["val_pr_auc"] + 0.01, f"{t['val_pr_auc']:.3f}", ha="center", fontsize=8,
                    color=INK["secondary"])
    axes[0].set_title("autoencoder (seed 0)", fontweight="normal", fontsize=10)
    axes[1].set_title("Mahalanobis burn-in", fontweight="normal", fontsize=10)
    axes[0].set_ylabel("VAL pooled PR-AUC")
    axes[0].set_ylim(0, 0.85)
    fig.suptitle("Equal budget: 4 configurations each, chosen on VAL only", x=0.01, y=1.04, ha="left",
                 fontweight="bold", fontsize=11)
    save(fig, HERE / "tuning_budget.svg")
    print("tuning:", [(lbl, round(t["val_pr_auc"], 3)) for lbl, t in zip(labels, neural)],
          [(t["shrinkage"], round(t["val_pr_auc"], 3)) for t in classical])


def fig_step_reaction() -> None:
    rx = synthetic["step_reaction"]
    rows = np.arange(80, 130)
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.axvline(100, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(99.5, 0.6, "step at row 100", transform=ax.get_xaxis_transform(), fontsize=8, color=INK["muted"],
            ha="right")
    for name, colour in (("causal", SERIES[0]), ("centred", SERIES[1])):
        s = np.array(rx[name]["scores"])
        ax.plot(rows, s, color=colour, label=f"{name} window: first rise at row {rx[name]['first_row_above_baseline']}")
    ax.set_xlabel("row")
    ax.set_ylabel("reconstruction error")
    ax.legend(loc="upper left")
    ax.set_title("A centred window 'detects' the step 7 rows before it happens (SYNTHETIC)")
    save(fig, HERE / "step_reaction.svg")
    print("step reaction:", {k: v["first_row_above_baseline"] for k, v in rx.items()})


def fig_best_of_k() -> None:
    """Handbook H7.6: expected best-of-k seeds versus the seed mean (SYNTHETIC example)."""
    best = {int(k): v for k, v in synthetic["best_of_k"].items()}
    mean = float(np.mean(synthetic["aps"]))
    ks = sorted(best)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.axhline(mean, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(ks[-1], mean - 0.006, f"seed mean {mean:.3f}", ha="right", va="top", fontsize=8, color=INK["muted"])
    ax.plot(ks, [best[k] for k in ks], marker="o", color=SERIES[0])
    for k in ks:
        ax.annotate(f"{best[k]:.3f}", (k, best[k]), textcoords="offset points", xytext=(0, 8), ha="center",
                    fontsize=8, color=INK["secondary"])
    ax.set_xticks(ks)
    ax.set_xlabel("number of seeds tried, best one reported")
    ax.set_ylabel("expected reported AP")
    ax.set_ylim(mean - 0.03, max(best.values()) + 0.025)
    ax.set_title("Reporting the best of k seeds inflates the result (SYNTHETIC, 10 seeds)")
    out = ROOT / "handbook" / "ch07_timeseries_grouped_modeling" / "figures" / "h7_6_best_of_k.svg"
    save(fig, out)
    print("best of k:", {k: round(best[k], 3) for k in ks}, "mean", round(mean, 3))


if __name__ == "__main__":
    fig_seed_spread()
    fig_learning_curves()
    fig_tuning()
    fig_step_reaction()
    fig_best_of_k()
