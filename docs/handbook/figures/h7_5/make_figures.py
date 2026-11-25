"""Figures for handbook section H7.5. Deterministic.

    python handbook/figures/h7_5/make_figures.py

Figure 1 is SYNTHETIC; figure 2 uses the REAL SKAB files (run `python project/get_skab.py` first).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
REF = ROOT / "solutions" / "labs" / "w4d2_classical_detectors" / "lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REF / "src"))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.detectors import PCADetector  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402
from flowguard.windowfeatures import window_features  # noqa: E402


def plant(n, rng):
    load, temp = rng.standard_normal(n), rng.standard_normal(n)
    mix = np.array([[1.0, 0.0], [0.9, 0.2], [0.8, -0.1], [0.0, 1.0], [0.1, 0.9], [0.5, 0.5]])
    x = np.column_stack([load, temp]) @ mix.T + 0.15 * rng.standard_normal((n, 6))
    return pd.DataFrame(x, columns=[f"s{i}" for i in range(1, 7)])


def fig_choice_of_k():
    rng = np.random.default_rng(0)
    train, normal = plant(5000, rng), plant(1000, rng)
    b = plant(300, rng)
    b["s2"] += 1.0                                   # broken relationship, as in the w4d2 example
    rows = []
    for k in range(1, 7):
        m = PCADetector(n_components=k).fit(train)
        y = np.r_[np.zeros(len(normal)), np.ones(len(b))]
        probe = pd.concat([normal, b])
        rows.append({"k": k, "explained": None, "Q_auc": roc_auc_score(y, m.score_q(probe)),
                     "T2_auc": roc_auc_score(y, m.score_t2(probe))})
    full = PCADetector(n_components=6).fit(train)
    share = np.cumsum(full.eigenvalues_) / full.eigenvalues_.sum()
    for r in rows:
        r["explained"] = float(share[r["k"] - 1])
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "choice_of_k.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(df["k"], df["Q_auc"], marker="o", color=SERIES[2], label="Q (SPE)")
    ax.plot(df["k"], df["T2_auc"], marker="o", color=SERIES[6], label="T2")
    ax.axhline(0.5, color=INK["muted"], lw=0.8, ls="--")
    ax.set_xticks(df["k"])
    ax.set_xticklabels([f"{k}\n{100 * e:.1f}%" for k, e in zip(df["k"], df["explained"])])
    ax.set_xlabel("retained components k / share of variance kept")
    ax.set_ylabel("ROC AUC, broken-relationship fault")
    ax.set_ylim(0.4, 1.08)
    ax.set_title("SYNTHETIC: as k grows, the broken relationship moves from Q to T2")
    ax.legend(loc="center left")
    save(fig, HERE / "choice_of_k.svg")


def fig_contributions():
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = load_splits(REF / "splits" / "v2.json")
    f = window_features(tidy, n_burn=100)
    f = f[f["t"] >= 100]
    zcols = [f"z_{s}" for s in SENSOR_COLUMNS]
    dev = f[f["experiment_id"].isin(dev_experiments(manifest)) & (f["anomaly"] == 0)]
    m = PCADetector(variance=0.8).fit(dev[zcols])
    rows = []
    for e in ("valve1/5", "other/14"):
        g = f[(f["experiment_id"] == e) & (f["anomaly"] == 1)]
        xs = (g[zcols].to_numpy() - m.mean_) / m.scale_
        resid = xs - (xs @ m.loadings_) @ m.loadings_.T
        contrib = (resid ** 2).mean(axis=0)
        for s, c in zip(SENSOR_COLUMNS, contrib):
            rows.append({"experiment": e, "sensor": s, "mean_Q_contribution": float(c),
                         "share": float(c / contrib.sum())})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "q_contributions.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(7.4, 3.4), sharey=True)
    for ax, (e, d) in zip(axes, df.groupby("experiment", sort=False)):
        ax.barh(d["sensor"], d["share"], color=SERIES[0])
        ax.set_title(f"{e}: fault rows", fontsize=10)
        ax.set_xlabel("share of Q")
        ax.invert_yaxis()
    fig.suptitle(f"REAL SKAB test faults: which sensors carry the Q statistic (PCA k = {m.k_} on 8 burn-in z)",
                 x=0.02, y=1.03, ha="left", fontsize=11, fontweight="bold")
    save(fig, HERE / "q_contributions.svg")
    return df, m.k_


if __name__ == "__main__":
    fig_choice_of_k()
    print(pd.read_csv(HERE / "choice_of_k.csv").round(3).to_string(index=False))
    try:
        df, k = fig_contributions()
        print("k =", k)
        print(df.pivot(index="sensor", columns="experiment", values="share").round(3))
    except FileNotFoundError as exc:
        print("skipping real-data figure:", exc)
