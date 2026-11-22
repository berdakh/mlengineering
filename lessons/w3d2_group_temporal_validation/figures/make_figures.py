"""Regenerate the figures of lesson w3d2 from the same code the lesson runs (about 3 minutes).

    python lessons/w3d2_group_temporal_validation/figures/make_figures.py

Figures 1 and 2 use SYNTHETIC data (the two example scripts). Figure 3 uses the REAL SKAB files and
needs `python project/get_skab.py` first; it is skipped with a message if they are absent.
matplotlib is an authoring dependency only; no lab or check imports it.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

ROW, GROUP, TRUTH = SERIES[1], SERIES[0], INK["primary"]     # "leaky" is always SERIES[1] in this lesson


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fig_optimism() -> None:
    rows = load(HERE.parent / "example" / "group_dependence.py", "group_dependence").part_a()
    rho = [r["rho"] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for key, colour, label, marker in (("row", ROW, "row-wise 5-fold", "o"), ("group", GROUP, "machine-wise 5-fold", "s"),
                                       ("truth", TRUTH, "truth: new machines", "D")):
        values = [r[key] for r in rows]
        ax.plot(rho, values, color=colour, marker=marker, label=label, linestyle="--" if key == "truth" else "-")
        ax.annotate(label, (rho[-1], values[-1]), xytext=(8, 0), textcoords="offset points", va="center",
                    color=INK["secondary"], fontsize=9)
    ax.set_xlim(-0.03, 1.12)
    ax.set_xticks(rho)
    ax.set_xlabel("intraclass correlation of the latent label (share of variance between machines)")
    ax.set_ylabel("accuracy")
    ax.set_title("Row-wise K-fold rises while accuracy on new machines falls (SYNTHETIC)")
    ax.legend(loc="lower left")
    save(fig, HERE / "optimism_vs_icc.svg")
    print("optimism_vs_icc:", [{k: round(v, 3) for k, v in r.items()} for r in rows])


def fig_purge() -> None:
    results = load(HERE.parent / "example" / "purge_demo.py", "purge_demo").run()
    names = list(results)
    mean = np.array([np.mean(v) for v in results.values()])
    sd = np.array([np.std(v) for v in results.values()])
    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    y = np.arange(len(names))[::-1]
    colours = [ROW if m - 0.5 > 2 * s else GROUP for m, s in zip(mean, sd)]
    ax.errorbar(mean, y, xerr=sd, fmt="none", ecolor=INK["muted"], elinewidth=1.2, capsize=3, zorder=2)
    ax.scatter(mean, y, color=colours, zorder=3)
    ax.axvline(0.5, color=TRUTH, linestyle="--", linewidth=1)
    ax.annotate("truth 0.5", (0.5, len(names) - 0.45), xytext=(4, 0), textcoords="offset points",
                color=INK["secondary"], fontsize=9, va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_ylim(-0.6, len(names) - 0.2)
    ax.set_xlabel("pooled out-of-fold ROC-AUC (mean and s.d. over 10 seeds)")
    ax.set_title("Unpredictable labels: every point right of 0.5 is leakage (SYNTHETIC)")
    ax.scatter([], [], color=ROW, label="more than 2 s.d. above 0.5")
    ax.scatter([], [], color=GROUP, label="within 2 s.d. of 0.5")
    ax.legend(loc="lower right")
    save(fig, HERE / "purge_demo.svg")
    print("purge_demo:", {n: (round(float(m), 3), round(float(s), 3)) for n, m, s in zip(names, mean, sd)})


def fig_skab() -> None:
    compare = load(ROOT / "solutions" / "lessons" / "w3d2_group_temporal_validation" / "lab" / "compare_schemes.py",
                   "compare_schemes")
    try:
        pool, results = compare.run()
    except FileNotFoundError as exc:
        print(f"skab_schemes: skipped ({exc})")
        return
    models = list(dict.fromkeys(r["model"] for r in results))
    schemes = list(dict.fromkeys(r["scheme"] for r in results))
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.9), sharey=True, sharex=True)
    y = np.arange(len(schemes))[::-1]
    for ax, model in zip(axes, models):
        sub = [r for r in results if r["model"] == model]
        for yi, r in zip(y, sub):
            folds = [v for _, v in r["per_fold"]]
            ax.scatter(folds, [yi] * len(folds), color=INK["muted"], s=14, zorder=2,
                       label="one fold" if yi == y[0] else None)
            ax.scatter([r["roc_auc"]], [yi], color=ROW if r["scheme"].startswith("1") else GROUP, s=60, zorder=3,
                       label="pooled, rows shuffled" if r["scheme"].startswith("1") else
                             ("pooled, other schemes" if yi == y[1] else None))
            ax.annotate(f"{r['roc_auc']:.3f}", (r["roc_auc"], yi), xytext=(0, 9), textcoords="offset points",
                        ha="center", fontsize=8, color=INK["secondary"])
        ax.axvline(0.5, color=TRUTH, linestyle="--", linewidth=1)
        ax.set_title(model, fontsize=10)
        ax.set_xlabel("ROC-AUC on held-out rows")
        ax.set_xlim(0.0, 1.03)
        ax.set_ylim(-0.6, len(schemes) - 0.3)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(schemes)
    axes[1].legend(loc="upper center", bbox_to_anchor=(-0.05, -0.16), ncols=3)
    n_dev = pool.split(" experiments")[0].split()[-1]
    fig.suptitle(f"Two models, six validation schemes: REAL SKAB data, {n_dev} development experiments (manifest v2)",
                 x=0.01, ha="left", fontweight="bold", fontsize=11)
    save(fig, HERE / "skab_schemes.svg")
    print("skab_schemes:", pool)
    for r in results:
        print(f"  {r['model'][:14]:<14} | {r['scheme']:<55} | ROC-AUC {r['roc_auc']:.3f} | PR-AUC {r['pr_auc']:.3f}")


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None          # optional: optimism | purge | skab
    for name, fn in (("optimism", fig_optimism), ("purge", fig_purge), ("skab", fig_skab)):
        if only in (None, name):
            fn()
