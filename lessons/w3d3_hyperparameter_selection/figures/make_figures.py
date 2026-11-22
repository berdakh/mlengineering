"""Regenerate every figure of lesson w3d3. Run from the repository root:

    python lessons/w3d3_hyperparameter_selection/figures/make_figures.py

Figures 1, 2 and 4 are SYNTHETIC simulations (NumPy, fixed seeds). Figure 3 plots the REAL SKAB
search recorded in ``skab_selection_run.json`` next to this file, which is a copy of the JSON written
by ``lab/selection_report.py`` (reference solution, 24 candidates, seed 0). To refresh it, rerun the
report and copy ``lab/runs/selection/selection_report.json`` over it. matplotlib is needed here only.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "example"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

import selection_demo as demo  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

HONEST, OPTIMISTIC, REFERENCE = SERIES[0], SERIES[1], INK["muted"]


def fig_optimism() -> None:
    rows = demo.part_a_b(np.random.default_rng(0))
    k = [r["K"] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(k, [r["independent"] for r in rows], marker="o", color=OPTIMISTIC, label="independent estimates")
    ax.plot(k, [r["rho_0.7"] for r in rows], marker="o", color=SERIES[2], label="estimates sharing noise (rho = 0.7)")
    ax.plot(k[1:], [r["bound"] for r in rows[1:]], linestyle="--", color=REFERENCE, label="bound  sigma * sqrt(2 ln K)")
    ax.set_xscale("log")
    ax.set_xlabel("K = number of candidates compared (log scale)")
    ax.set_ylabel("best estimate minus true score")
    ax.set_title("The best of K equally good candidates looks better as K grows\n(SYNTHETIC; every candidate has the same true score, s.e. 0.02)")
    for key, text in (("independent", "independent"), ("rho_0.7", "shared noise"), ("bound", "bound")):
        ax.annotate(text, (k[-1], rows[-1][key]), xytext=(8, 0), textcoords="offset points", va="center", color=INK["secondary"])
    ax.set_xlim(0.8, 4000)
    ax.legend(loc="upper left")
    save(fig, HERE / "optimism_of_max.svg")
    print("optimism_of_max.svg:", [(r["K"], round(r["independent"], 4), round(r["rho_0.7"], 4), round(r["bound"], 4)) for r in rows])


def fig_grid_vs_random() -> None:
    rng = np.random.default_rng(3)
    curve_x = np.linspace(-3, 3, 200)
    tried = {"4 x 4 grid: 4 distinct values of C": np.repeat(np.linspace(-3, 3, 4), 4),
             "16 random trials: 16 distinct values of C": rng.uniform(-3, 3, 16)}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharey=True)
    for ax, (title, xs) in zip(axes, tried.items()):
        ys = demo.response(xs, np.zeros_like(xs))
        ax.plot(curve_x, demo.response(curve_x, 0), color=REFERENCE, linewidth=1.5, label="validation score as a function of C")
        ax.scatter(xs, ys, color=SERIES[0], zorder=3, label="trials")
        best = int(np.argmax(ys))
        ax.scatter([xs[best]], [ys[best]], s=110, facecolors="none", edgecolors=INK["primary"], linewidths=1.5, zorder=4, label="best found")
        ax.annotate(f"best found {ys[best]:.3f}", (xs[best], ys[best]), xytext=(8, -18), textcoords="offset points", color=INK["secondary"])
        ax.set_title(title)
        ax.set_xlabel("log10 C  (the hyperparameter that matters)")
        print("grid_vs_random.svg:", title, "best", round(float(ys[best]), 4))
    axes[0].set_ylabel("validation score")
    axes[0].legend(loc="lower center", fontsize=8)
    fig.suptitle("Same budget, one important hyperparameter: random search tries more values of it (SYNTHETIC)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, HERE / "grid_vs_random.svg")


def fig_skab_trials() -> None:
    run = json.loads((HERE / "skab_selection_run.json").read_text())
    trials = sorted(run["trials"], key=lambda t: t["mean"])
    nested, test = run["nested"], run["test_pr_auc"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for family, colour in (("logreg", SERIES[2]), ("hgb", SERIES[3])):
        idx = [i for i, t in enumerate(trials) if t["params"]["model"] == family]
        ax.errorbar(idx, [trials[i]["mean"] for i in idx], yerr=[trials[i]["se"] for i in idx], fmt="o", color=colour,
                    ecolor=INK["axis"], elinewidth=1.2, capsize=0,
                    label={"logreg": "logistic regression trials", "hgb": "gradient boosting trials"}[family])
    n = len(trials)
    ax.axhspan(nested["mean"] - nested["se"], nested["mean"] + nested["se"], color=HONEST, alpha=0.12)
    ax.axhline(nested["mean"], color=HONEST, linewidth=1.8)
    ax.axhline(trials[-1]["mean"], color=OPTIMISTIC, linewidth=1.8, linestyle="--")
    ax.axhline(test, color=INK["primary"], linewidth=1.2, linestyle=":")
    ax.text(0.2, nested["mean"] + 0.002, f"nested estimate {nested['mean']:.3f} (band: +/- 1 SE)",
            color=INK["secondary"], va="bottom")
    ax.text(0.2, trials[-1]["mean"] + 0.004, f"best trial's own dev score {trials[-1]['mean']:.3f}", color=INK["secondary"], va="bottom")
    n_test = len(json.loads((HERE.parent / "lab" / "splits" / "v2.json").read_text())["test"])
    ax.text(0.2, test + 0.004, f"test, {n_test} experiments, one look {test:.3f}", color=INK["secondary"], va="bottom")
    ax.set_xlim(-0.8, n - 0.2)
    ax.set_xticks([])
    ax.set_xlabel(f"{n} recorded trials, sorted by dev score")
    ax.set_ylabel("point-level PR-AUC (dev: mean over 4 grouped folds, bar = SE)")
    ax.set_title("Real SKAB search: trial error bars overlap; three 'performance' numbers disagree")
    ax.legend(loc="lower right")
    save(fig, HERE / "skab_trials.svg")
    print("skab_trials.svg: best", round(trials[-1]["mean"], 3), "nested", round(nested["mean"], 3), "+/-", round(nested["se"], 3),
          "test", round(test, 3), "min", round(trials[0]["mean"], 3))


def fig_threshold() -> None:
    rng = np.random.default_rng(4)

    def sample(n, shift, offset):
        y = (rng.random(n) < 0.3).astype(int)
        return rng.standard_normal(n) + shift * y + offset, y

    def f1_curve(s, y, grid):
        out = []
        for v in grid:
            flagged = s >= v
            tp = np.sum(flagged & (y == 1))
            out.append(0.0 if tp == 0 else 2 * tp / (2 * tp + np.sum(flagged & (y == 0)) + np.sum(~flagged & (y == 1))))
        return np.array(out)

    dev_s, dev_y = sample(1500, 1.6, 0.0)
    test_s, test_y = sample(1500, 1.6, 0.5)          # the score distribution has drifted upward on test
    grid = np.linspace(-1.5, 3.5, 251)
    dev_f1, test_f1 = f1_curve(dev_s, dev_y, grid), f1_curve(test_s, test_y, grid)
    frozen = grid[int(np.argmax(dev_f1))]
    at_frozen = test_f1[int(np.argmax(dev_f1))]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.plot(grid, dev_f1, color=HONEST, label="development")
    ax.plot(grid, test_f1, color=OPTIMISTIC, label="test")
    ax.axvline(frozen, color=INK["primary"], linewidth=1.0, linestyle=":")
    ax.scatter([frozen], [at_frozen], color=INK["primary"], zorder=4)
    ax.scatter([grid[int(np.argmax(test_f1))]], [test_f1.max()], s=110, facecolors="none", edgecolors=OPTIMISTIC, linewidths=1.5, zorder=4)
    ax.annotate(f"reportable: test F1 at the\nfrozen threshold = {at_frozen:.3f}", (frozen, at_frozen), xytext=(-1.4, 0.22), textcoords="data",
                color=INK["secondary"], arrowprops={"arrowstyle": "-", "color": INK["axis"]})
    ax.annotate(f"not reportable: best F1 on test = {test_f1.max():.3f}", (grid[int(np.argmax(test_f1))], test_f1.max()), xytext=(1.25, 0.86),
                textcoords="data", color=INK["secondary"], arrowprops={"arrowstyle": "-", "color": INK["axis"]})
    ax.text(frozen, 0.03, " threshold chosen on dev", color=INK["secondary"], ha="left")
    ax.set_xlabel("decision threshold on the score")
    ax.set_ylabel("F1")
    ax.set_ylim(0, 1)
    ax.set_title("A threshold is a fitted parameter: choose it on dev, freeze it, report test there\n(SYNTHETIC; test scores shifted by +0.5)")
    ax.legend(loc="lower right")
    save(fig, HERE / "threshold_frozen.svg")
    print("threshold_frozen.svg: frozen threshold", round(float(frozen), 2), "dev F1", round(float(dev_f1.max()), 3),
          "test F1 at frozen", round(float(at_frozen), 3), "test-optimal F1", round(float(test_f1.max()), 3))


if __name__ == "__main__":
    fig_optimism()
    fig_grid_vs_random()
    fig_threshold()
    if (HERE / "skab_selection_run.json").is_file():
        fig_skab_trials()
    else:
        print("skab_selection_run.json missing: skipped skab_trials.svg")
