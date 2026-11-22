"""Regenerate every figure of lesson w4d2. Deterministic. About 3 minutes (it re-runs the comparison).

    python project/get_skab.py                                          # once (real-data figures)
    python lessons/w4d2_classical_detectors/figures/make_figures.py

Writes figures/*.svg and figures/*.csv. Uses the REFERENCE package in solutions/.
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
REF = ROOT / "solutions" / "lessons" / "w4d2_classical_detectors" / "lab"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REF / "src"))
sys.path.insert(0, str(REF))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.data import load_raw  # noqa: E402
from flowguard.detectors import PCADetector  # noqa: E402
from flowguard.metrics import best_f1_threshold  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402
from flowguard.windowfeatures import feature_columns, window_features  # noqa: E402

BURN_IN = 100


def fig_geometry():
    rng = np.random.default_rng(0)
    a = rng.standard_normal(1500)
    x = pd.DataFrame({"s1": a, "s2": 0.95 * a + 0.25 * rng.standard_normal(1500)})
    pca = PCADetector(n_components=1).fit(x)
    pts = pd.DataFrame({"s1": [2.6, 1.0], "s2": [2.5, -1.0]}, index=["A: far along the normal direction",
                                                                       "B: breaks the s1-s2 relationship"])
    t2, q = pca.score_t2(pts), pca.score_q(pts)
    pd.DataFrame({"point": pts.index, "s1": pts["s1"], "s2": pts["s2"], "T2": t2, "Q": q,
                  "T2_limit": pca.t2_limit_, "Q_limit": pca.q_limit_}).to_csv(HERE / "t2_q_geometry.csv", index=False)
    fig, ax = plt.subplots(figsize=(5.6, 5.0))
    ax.scatter(x["s1"], x["s2"], s=6, color=INK["muted"], alpha=0.35, lw=0, label="normal rows (fit data)")
    line = np.linspace(-3.5, 3.5, 2)
    direction = pca.loadings_[:, 0] * pca.scale_
    direction = direction / np.linalg.norm(direction)
    ax.plot(pca.mean_[0] + line * direction[0], pca.mean_[1] + line * direction[1], color=SERIES[0], lw=2,
            label="retained component")
    for (name, row), c, tv, qv in zip(pts.iterrows(), (SERIES[1], SERIES[2]), t2, q):
        ax.plot(row["s1"], row["s2"], "o", color=c, markersize=9, markeredgecolor=INK["surface"], mew=1.5)
        ax.annotate(f"{name}\nT2 = {tv:.1f} (limit {pca.t2_limit_:.1f}), Q = {qv:.2f} (limit {pca.q_limit_:.2f})",
                    (row["s1"], row["s2"]), xytext=(-10, 14) if row["s2"] > 0 else (12, -6),
                    textcoords="offset points", fontsize=8, color=INK["primary"],
                    ha="right" if row["s2"] > 0 else "left")
    ax.set_xlabel("sensor s1 (standard units)")
    ax.set_ylabel("sensor s2 (standard units)")
    ax.set_xlim(-4, 4)
    ax.set_ylim(-4, 4)
    ax.set_aspect("equal")
    ax.set_title("SYNTHETIC: T2 measures distance along the model, Q distance from it")
    ax.legend(loc="lower right", fontsize=8)
    save(fig, HERE / "t2_q_geometry.svg")


def fig_example_auc():
    out = subprocess.run([sys.executable, str(ROOT / "lessons" / "w4d2_classical_detectors" / "example" /
                                              "detectors_tour.py")], check=True, capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if line.strip().startswith(("PCA T2", "PCA Q", "isolation forest")) and "fault A" in line:
            name = line.split("fault A")[0].strip()
            rows.append({"detector": name, "fault": "A: extreme but consistent", "auc": float(parts[-4])})
            rows.append({"detector": name, "fault": "B: broken relationship", "auc": float(parts[-1])})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "example_auc.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    dets = list(dict.fromkeys(df["detector"]))
    width = 0.36
    for j, (fault, c) in enumerate(zip(df["fault"].unique(), (SERIES[1], SERIES[2]))):
        vals = [df[(df.detector == d) & (df.fault == fault)]["auc"].iloc[0] for d in dets]
        xs = np.arange(len(dets)) + (j - 0.5) * width
        ax.bar(xs, vals, width=width - 0.04, color=c, label=f"fault {fault}")
        for xv, v in zip(xs, vals):
            ax.text(xv, v + 0.01, f"{v:.2f}", ha="center", fontsize=8, color=INK["secondary"])
    ax.axhline(0.5, color=INK["muted"], lw=0.8, ls="--")
    ax.set_xticks(range(len(dets)))
    ax.set_xticklabels(dets)
    ax.set_ylim(0.4, 1.08)
    ax.set_ylabel("ROC AUC vs normal rows")
    ax.set_title("SYNTHETIC: T2 and Q each see one kind of fault; the forest sees both, partly")
    ax.legend(loc="upper center", ncol=2, fontsize=8, bbox_to_anchor=(0.5, -0.12))
    save(fig, HERE / "example_auc.svg")


def fig_protocols():
    out = HERE / "comparison.json"
    subprocess.run([sys.executable, str(REF / "compare_detectors.py"), "--json", str(out)], check=True,
                   stdout=subprocess.DEVNULL)
    res = json.loads(out.read_text())
    out.unlink()
    a, b = pd.DataFrame(res["A"]), pd.DataFrame(res["B"])
    df = a[["detector", "pr_auc", "low", "high", "config", "oof_dev_pr_auc", "false_alarms_per_hour",
            "detected", "events", "median_delay_s", "best_index"]].merge(
        b[["detector", "pr_auc", "low", "high"]], on="detector", suffixes=("_A_test", "_B_unseen_family"))
    df.to_csv(HERE / "protocols.csv", index=False)
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for pos, (_, r) in enumerate(df.iloc[::-1].iterrows()):
        for key, c, off, lab in (("A_test", SERIES[0], 0.14, "protocol A: frozen test set (7 experiments)"),
                                 ("B_unseen_family", SERIES[1], -0.14,
                                  "protocol B: unseen family `other` (8 clusters)")):
            ax.plot([r[f"low_{key}"], r[f"high_{key}"]], [pos + off] * 2, color=c, lw=2, solid_capstyle="round",
                    label=lab if pos == 0 else None)
            ax.plot(r[f"pr_auc_{key}"], pos + off, "o", color=c, markersize=6, markeredgecolor=INK["surface"], mew=1.2)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["detector"].iloc[::-1], fontsize=8)
    ax.set_xlim(0.35, 1.0)
    ax.set_xlabel("point-level PR-AUC (95% cluster-bootstrap interval)")
    ax.set_title("REAL SKAB: the supervised model wins on known faults and drops on an unseen family")
    ax.legend(loc="upper center", fontsize=8, ncol=2, bbox_to_anchor=(0.45, -0.18))
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "protocols.svg")
    return df


def fig_skab_scores(protocols: pd.DataFrame):
    sys.path.insert(0, str(REF))
    import compare_detectors as cd
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = load_splits(REF / "splits" / "v2.json")
    frame = window_features(tidy, n_burn=BURN_IN)
    frame = frame[frame["t"] >= BURN_IN]
    cols = feature_columns(frame)
    dev = frame[frame["experiment_id"].isin(dev_experiments(manifest))]
    e = "valve1/5"
    one = frame[frame["experiment_id"] == e].sort_values("t")
    fig, axes = plt.subplots(4, 1, figsize=(7.2, 6.4), sharex=True)
    names = ["flow_rate abs z (w2d6 baseline)", "PCA T2", "isolation forest", "gradient-boosted trees"]
    rows = {"t": one["t"].to_numpy(), "anomaly": one["anomaly"].to_numpy()}
    for ax, name, c in zip(axes, names, (SERIES[0], SERIES[6], SERIES[2], SERIES[1])):
        mode, makers = cd.DETECTORS[name]
        best = int(protocols.loc[protocols["detector"] == name, "best_index"].iloc[0])
        oof = np.zeros(len(dev))
        for fold in manifest["dev_folds"]:
            held = dev["experiment_id"].isin(fold).to_numpy()
            oof[held] = cd.fit_score(makers[best], mode, dev[~held], dev[held], cols)
        thr, _ = best_f1_threshold(dev["anomaly"].to_numpy(), oof)
        ref = np.sort(oof)                       # percentile within the development scores: comparable
        pct = lambda v: 100.0 * np.searchsorted(ref, v, side="right") / len(ref)  # noqa: E731
        s = pct(cd.fit_score(makers[best], mode, dev, one, cols))
        rows[name] = s
        ax.plot(one["t"], s, color=c, lw=0.9)
        ax.axhline(pct(thr), color=INK["muted"], lw=0.8, ls="--")
        ax.set_ylabel(name.replace(" (w2d6 baseline)", ""), fontsize=8)
        ax.set_ylim(-3, 103)
        ax.set_yticks([0, 50, 100])
        an = one["anomaly"].to_numpy()
        on = np.flatnonzero(np.diff(np.r_[0, an, 0]) == 1)
        off = np.flatnonzero(np.diff(np.r_[0, an, 0]) == -1)
        tt = one["t"].to_numpy()
        for s0, s1 in zip(on, off):
            ax.axvspan(tt[s0], tt[s1 - 1], color=SERIES[1], alpha=0.12, lw=0)
    axes[0].set_title(f"REAL SKAB test experiment {e}: score as a percentile of development scores; dashed = threshold")
    axes[-1].set_xlabel("row t (about 1 s)")
    pd.DataFrame(rows).to_csv(HERE / "skab_scores_valve1_5.csv", index=False)
    save(fig, HERE / "skab_scores.svg")


def main() -> None:
    fig_geometry()
    fig_example_auc()
    try:
        load_raw(ROOT / "data" / "raw" / "skab")
    except FileNotFoundError as exc:
        print(f"skipping real-data figures: {exc}")
        return
    protocols = fig_protocols()
    fig_skab_scores(protocols)
    print(protocols[["detector", "pr_auc_A_test", "pr_auc_B_unseen_family"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
