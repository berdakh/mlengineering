"""Figures for w2d4 and handbook H1.1 / H1.2.

    python project/get_skab.py        # once
    python lessons/w2d4_problem_framing_splits/figures/make_figures.py     # about 30 s

1. split_layout.svg       - the frozen v1 manifest as a grid (real experiment ids).
2. row_vs_experiment.svg  - per-fold scores of the same model under row-level and
                            experiment-level 4-fold validation (REAL SKAB, development experiments only;
                            same code path as example/skab_row_vs_experiment.py).
3. recall_interval.svg    - how wide a 95 % interval for event recall is with n test events (exact arithmetic).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "example"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

REFERENCE = ROOT / "solutions" / "lessons" / "w2d4_problem_framing_splits" / "lab"
MANIFEST = json.loads((REFERENCE / "splits" / "v1.json").read_text())
ROLE_COLOUR = {"test": SERIES[1], "dev fold 1": "#cde2fb", "dev fold 2": "#9ec5f4", "dev fold 3": "#6da7ec",
               "dev fold 4": "#256abf"}
ROW, EXPERIMENT = SERIES[1], SERIES[0]   # "row-level" is the optimistic estimate throughout the lesson


def split_layout() -> None:
    role = {e: "test" for e in MANIFEST["test"]}
    for i, fold in enumerate(MANIFEST["dev_folds"], start=1):
        role.update({e: f"dev fold {i}" for e in fold})
    families = [("valve1", 16), ("valve2", 4), ("other", 14)]
    fig, ax = plt.subplots(figsize=(8.6, 2.9))
    for y, (fam, _) in enumerate(families):
        ids = sorted((e for e in role if e.startswith(fam + "/")), key=lambda e: int(e.split("/")[1]))
        for x, e in enumerate(ids):
            r = role[e]
            ax.add_patch(plt.Rectangle((x + 0.04, y + 0.1), 0.92, 0.8, color=ROLE_COLOUR[r]))
            dark = r in ("test", "dev fold 4")
            ax.text(x + 0.5, y + 0.5, e.split("/")[1], ha="center", va="center", fontsize=9,
                    color="#ffffff" if dark else INK["primary"])
        counts = {k: sum(role[e] == k for e in ids) for k in ROLE_COLOUR}
        print(fam, counts)
    ax.set_xlim(0, 16)
    ax.set_ylim(len(families), 0)
    ax.set_yticks([i + 0.5 for i in range(len(families))], [f"{f} ({n})" for f, n in families])
    ax.set_xticks([])
    ax.grid(visible=False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Split manifest v1: every experiment (numbered cell) has exactly one role (real ids)")
    ax.legend(handles=[Patch(color=c, label=k) for k, c in ROLE_COLOUR.items()],
              loc="upper center", bbox_to_anchor=(0.5, -0.03), ncol=5)
    save(fig, HERE / "split_layout.svg")


def row_vs_experiment() -> None:
    raw = ROOT / "data" / "raw" / "skab"
    if not raw.is_dir():
        sys.exit("data/raw/skab not found. Run:  python project/get_skab.py")
    import skab_row_vs_experiment as ex
    from sklearn.model_selection import KFold

    tidy = ex.load_raw(raw)
    folds = MANIFEST["dev_folds"]
    dev = tidy[tidy["experiment_id"].isin([e for f in folds for e in f])].reset_index(drop=True)
    X, y = dev[list(ex.SENSOR_COLUMNS)].to_numpy(), dev["anomaly"].to_numpy()
    row = np.array([ex.scores(X[tr], y[tr], X[te], y[te]) for tr, te in KFold(4, shuffle=True, random_state=0).split(X)])
    exp = []
    for held in folds:
        te = dev["experiment_id"].isin(held).to_numpy()
        exp.append(ex.scores(X[~te], y[~te], X[te], y[te]))
    exp = np.array(exp)
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.4), sharey=True)
    for ax, col, name in zip(axes, (0, 1), ("PR-AUC", "ROC-AUC")):
        for x, (vals, colour) in enumerate(((row[:, col], ROW), (exp[:, col], EXPERIMENT))):
            ax.scatter([x] * 4, vals, s=46, color=colour, edgecolor=INK["surface"], linewidth=1.4, zorder=3)
            ax.hlines(vals.mean(), x - 0.22, x + 0.22, color=colour, linewidth=2.5)
            ax.text(x + 0.27, vals.mean(), f"{vals.mean():.3f}", va="center", color=INK["primary"])
        ax.set_xticks([0, 1], ["rows shuffled\ninto folds", "whole experiments\nheld out"])
        ax.set_xlim(-0.5, 1.75)
        ax.set_title(name, fontweight="normal")
        ax.grid(axis="x", visible=False)
        print(name, "row-level folds", np.round(row[:, col], 3), "mean", round(row[:, col].mean(), 3),
              "| experiment-level folds", np.round(exp[:, col], 3), "mean", round(exp[:, col].mean(), 3))
    axes[0].set_ylabel("score on held-out fold (dot = fold, bar = mean)")
    axes[0].set_ylim(0.7, 1.0)
    fig.suptitle("Same model, same data: the split unit decides the number (real SKAB, 25 dev experiments)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, HERE / "row_vs_experiment.svg")


def recall_interval() -> None:
    from math import sqrt
    p = 0.8
    ns = np.array([5, 9, 20, 34, 50, 100, 200])
    half = 1.96 * np.sqrt(p * (1 - p) / ns)
    fig, ax = plt.subplots(figsize=(6.4, 3.3))
    ax.vlines(range(len(ns)), np.clip(p - half, 0, 1), np.clip(p + half, 0, 1), color=SERIES[0], linewidth=4)
    ax.scatter(range(len(ns)), [p] * len(ns), s=40, color=INK["primary"], zorder=3)
    for i, (n, h) in enumerate(zip(ns, half)):
        ax.text(i, min(p + h, 1.0) + 0.02, f"±{h:.2f}", ha="center", color=INK["primary"], fontsize=9)
    ax.set_xticks(range(len(ns)), [f"{n}\n{'test set v1' if n == 9 else 'all of SKAB' if n == 34 else ''}" for n in ns])
    ax.set_ylim(0.3, 1.12)
    ax.set_xlabel("number of test events n")
    ax.set_ylabel("event recall")
    ax.set_title("Normal-approximation 95 % interval around a true recall of 0.8")
    ax.grid(axis="x", visible=False)
    save(fig, HERE / "recall_interval.svg")
    print("n", ns.tolist(), "SE", np.round(np.sqrt(p * (1 - p) / ns), 3).tolist(), "half-width", np.round(half, 3).tolist())
    _ = sqrt


if __name__ == "__main__":
    split_layout()
    row_vs_experiment()
    recall_interval()
