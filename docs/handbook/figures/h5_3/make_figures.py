"""Figures for handbook section H5.3 (all SYNTHETIC). Deterministic.

    python handbook/figures/h5_3/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import (BaggingClassifier, HistGradientBoostingClassifier, IsolationForest,
                              RandomForestClassifier)
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(ROOT))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402


def fig_ensembles():
    x, y = make_classification(n_samples=6000, n_features=20, n_informative=6, n_redundant=6,
                               flip_y=0.05, class_sep=0.8, random_state=0)
    xtr, ytr, xte, yte = x[:3000], y[:3000], x[3000:], y[3000:]
    rows = []
    single = roc_auc_score(yte, DecisionTreeClassifier(random_state=0).fit(xtr, ytr).predict_proba(xte)[:, 1])
    for b in (1, 5, 10, 25, 50, 100, 200):
        bag = BaggingClassifier(DecisionTreeClassifier(), n_estimators=b, random_state=0).fit(xtr, ytr)
        rf = RandomForestClassifier(n_estimators=b, max_features="sqrt", random_state=0).fit(xtr, ytr)
        rows.append({"trees": b, "bagged trees": roc_auc_score(yte, bag.predict_proba(xte)[:, 1]),
                     "random forest": roc_auc_score(yte, rf.predict_proba(xte)[:, 1])})
    df = pd.DataFrame(rows)
    df["single deep tree"] = single
    df.to_csv(HERE / "ensembles.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for col, c in (("random forest", SERIES[0]), ("bagged trees", SERIES[2])):
        ax.plot(df["trees"], df[col], marker="o", color=c, label=col)
    ax.axhline(single, color=INK["muted"], ls="--", lw=1, label="single deep tree")
    ax.set_xscale("log")
    ax.set_xticks([1, 5, 10, 25, 50, 100, 200])
    ax.set_xticklabels(["1", "5", "10", "25", "50", "100", "200"])
    ax.set_xlabel("number of trees")
    ax.set_ylabel("test ROC AUC")
    ax.set_title("SYNTHETIC: averaging trees removes variance; decorrelating them removes more")
    ax.legend(loc="lower right")
    save(fig, HERE / "ensembles.svg")


def fig_boosting():
    x, y = make_classification(n_samples=6000, n_features=20, n_informative=6, n_redundant=6,
                               flip_y=0.05, class_sep=0.8, random_state=1)
    xtr, ytr, xte, yte = x[:3000], y[:3000], x[3000:], y[3000:]
    rows = []
    for lr in (0.5, 0.1, 0.02):
        m = HistGradientBoostingClassifier(learning_rate=lr, max_iter=400, early_stopping=False,
                                           random_state=0).fit(xtr, ytr)
        for i, p in enumerate(m.staged_predict_proba(xte), start=1):
            if i in (1, 2, 5, 10, 20, 50, 100, 200, 400):
                rows.append({"learning_rate": lr, "iterations": i, "test_log_loss": log_loss(yte, p[:, 1])})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "boosting.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for (lr, d), c in zip(df.groupby("learning_rate", sort=False), (SERIES[1], SERIES[0], SERIES[2])):
        ax.plot(d["iterations"], d["test_log_loss"], marker="o", markersize=4, color=c, label=f"learning rate {lr}")
    ax.set_xscale("log")
    ax.set_xticks([1, 2, 5, 10, 20, 50, 100, 200, 400])
    ax.set_xticklabels(["1", "2", "5", "10", "20", "50", "100", "200", "400"])
    ax.set_xlabel("boosting iterations")
    ax.set_ylabel("test log loss")
    ax.set_title("SYNTHETIC: a large learning rate fits fast and then over-fits")
    ax.legend()
    save(fig, HERE / "boosting.svg")


def fig_isolation():
    rng = np.random.default_rng(0)
    x = rng.standard_normal((2000, 2))
    forest = IsolationForest(n_estimators=200, random_state=0).fit(x)
    radii = np.linspace(0, 6, 25)
    probes = np.column_stack([radii, np.zeros_like(radii)])
    depths = []
    for est, feats in zip(forest.estimators_, forest.estimators_features_):
        node_counts = est.decision_path(probes[:, feats]).sum(axis=1)
        depths.append(np.asarray(node_counts).ravel() - 1)
    mean_depth = np.mean(depths, axis=0)
    df = pd.DataFrame({"distance_from_centre": radii, "mean_tree_depth_reached": mean_depth,
                       "score_samples": forest.score_samples(probes)})
    df.to_csv(HERE / "isolation_depth.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.2))
    axes[0].scatter(x[:, 0], x[:, 1], s=4, color=INK["muted"], alpha=0.4, lw=0)
    axes[0].plot(radii, np.zeros_like(radii), "o", color=SERIES[1], markersize=3)
    axes[0].set_xlim(-4, 6.5)
    axes[0].set_ylim(-4, 4)
    axes[0].set_aspect("equal")
    axes[0].set_title("probe points along a ray", fontsize=10)
    axes[1].plot(radii, mean_depth, color=SERIES[0], marker="o", markersize=3)
    axes[1].set_xlabel("distance of the probe from the centre (SD)")
    axes[1].set_ylabel("mean depth reached (splits)")
    axes[1].set_title("fewer splits for outliers, then a plateau", fontsize=10)
    fig.suptitle("SYNTHETIC isolation forest (200 trees, 256-row subsamples)", x=0.02, y=1.03, ha="left",
                 fontsize=11, fontweight="bold")
    save(fig, HERE / "isolation_depth.svg")


if __name__ == "__main__":
    fig_ensembles()
    fig_boosting()
    fig_isolation()
    for f in ("ensembles", "boosting", "isolation_depth"):
        print(f, "\n", pd.read_csv(HERE / f"{f}.csv").round(3).to_string(index=False))
