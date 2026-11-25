"""Regenerate every figure of lesson w3d5 (deterministic).

    python labs/w3d5_uncertainty/figures/make_figures.py          # about 1.5 minutes

Figures 1 and 4 use SYNTHETIC data or pure formulas. Figures 2 and 3 use REAL SKAB results:
figure 2 recomputes them from data/raw/skab (run `python project/get_skab.py` first; skipped with a
message if the data is absent), figure 3 reads the committed per-cluster results in
challenge/per_cluster_pr_auc.csv. The plotted numbers are printed and written to figures/*.csv.
matplotlib is needed only here; the lab and the checks do not import it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = UNIT.parents[1]
REFERENCE_LAB = ROOT / "solutions" / "labs" / "w3d5_uncertainty" / "lab"
sys.path[:0] = [str(ROOT), str(UNIT / "example"), str(REFERENCE_LAB), str(REFERENCE_LAB / "src")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

ROW, CLUSTER = SERIES[1], SERIES[0]        # "wrong unit" is always SERIES[1], "correct unit" SERIES[0]


def fig_coverage() -> None:
    import coverage_simulation as cs
    df = pd.DataFrame(cs.run())
    df.to_csv(HERE / "coverage.csv", index=False)
    print(df.round(3).to_string(index=False))
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 3.4), sharey=True)
    for ax, g in zip(axes, (30, 9, 7)):
        d = df[df["clusters"] == g]
        x = np.arange(len(d))
        ax.axhline(0.95, color=INK["muted"], linewidth=1, linestyle="--")
        ax.plot(x, d["row_coverage"], marker="o", color=ROW, label="row bootstrap")
        ax.plot(x, d["cluster_coverage"], marker="s", color=CLUSTER, label="cluster bootstrap")
        for xi, (r, c) in enumerate(zip(d["row_coverage"], d["cluster_coverage"])):
            up, down = (7, -14)                              # the larger value is labelled above its marker
            ax.annotate(f"{r:.2f}", (xi, r), textcoords="offset points", xytext=(0, up if r > c else down),
                        ha="center", fontsize=8, color=INK["secondary"])
            ax.annotate(f"{c:.2f}", (xi, c), textcoords="offset points", xytext=(0, down if r > c else up),
                        ha="center", fontsize=8, color=INK["secondary"])
        ax.set_xticks(x, [f"{v:.1f}" for v in d["icc"]])
        ax.set_xlim(-0.4, 2.4)
        ax.set_xlabel("intraclass correlation")
        ax.set_title(f"{g} clusters", fontweight="normal", fontsize=10)
    axes[0].set_ylabel("share of intervals containing the truth")
    axes[0].set_ylim(0.2, 1.08)
    axes[1].text(2.35, 1.0, "nominal 0.95", fontsize=8, color=INK["muted"], ha="right")
    axes[0].legend(loc="lower left")
    fig.suptitle("Row-level intervals collapse under dependence; cluster intervals undercover with few clusters "
                 "(SYNTHETIC)", x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, HERE / "coverage.svg")


def fig_skab_intervals() -> None:
    raw = ROOT / "data" / "raw" / "skab"
    if not raw.is_dir():
        print("skab_intervals: data/raw/skab not found, run `python project/get_skab.py`; figure skipped")
        return
    import baseline_intervals as bi
    from flowguard.baselines import MahalanobisScorer, SingleSensorZScorer, burn_in_scores
    from flowguard.data import load_raw
    from flowguard.splits import load_splits
    from flowguard.uncertainty import cluster_bootstrap

    tidy = load_raw(raw)
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    test = manifest["test"]
    cluster_of = bi.cluster_ids(manifest, test)
    scores = {
        "elapsed time\n(no sensors)": tidy["t"].to_numpy(dtype=float),
        "Mahalanobis,\nburn-in": burn_in_scores(MahalanobisScorer, tidy, bi.BURN_IN),
        "flow-rate z,\nburn-in": burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, bi.BURN_IN),
        "logistic regression\n(supervised)": bi.supervised_scores(tidy, manifest, bi.BURN_IN),
    }
    rows = []
    for name, s in scores.items():
        res = bi.per_cluster(tidy, s, test, cluster_of)
        ci = cluster_bootstrap(bi.pooled_pr_auc, res, n_boot=2000, seed=0)
        y = np.concatenate([r["y"] for r in res.values()])
        sc = np.concatenate([r["s"] for r in res.values()])
        low, high = bi.row_bootstrap(y, sc, n_boot=300, seed=0)
        rows.append({"baseline": name.replace("\n", " "), "label": name, "estimate": ci["estimate"],
                     "cluster_low": ci["low"], "cluster_high": ci["high"], "row_low": low, "row_high": high})
    df = pd.DataFrame(rows)
    df.drop(columns="label").to_csv(HERE / "skab_intervals.csv", index=False)
    print(df.drop(columns="label").round(3).to_string(index=False))
    fig, ax = plt.subplots(figsize=(7.6, 3.4))
    ypos = np.arange(len(df))
    ax.hlines(ypos + 0.13, df["cluster_low"], df["cluster_high"], color=CLUSTER, linewidth=5,
              label="cluster bootstrap (7 independent clusters)")
    ax.hlines(ypos - 0.13, df["row_low"], df["row_high"], color=ROW, linewidth=5,
              label="row bootstrap (rows treated as independent)")
    ax.plot(df["estimate"], ypos, "o", color=INK["primary"], markersize=5, label="point estimate")
    ax.set_yticks(ypos, df["label"])
    ax.set_ylim(-0.6, len(df) - 0.4)
    ax.set_xlabel("pooled point-level PR-AUC on the test set, 95% interval")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower left", bbox_to_anchor=(0.0, 1.02), ncols=1, borderaxespad=0)
    ratio = (df["cluster_high"] - df["cluster_low"]) / (df["row_high"] - df["row_low"])
    ax.set_title(f"Real SKAB: the row-level interval is {ratio.min():.0f} to {ratio.max():.0f} times too narrow", y=1.32)
    save(fig, HERE / "skab_intervals.svg")


def fig_paired_differences() -> None:
    df = pd.read_csv(UNIT / "challenge" / "per_cluster_pr_auc.csv")
    panels = [("logreg", "supervised logistic regression minus flow-rate z"),
              ("mahalanobis", "Mahalanobis minus flow-rate z")]
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.6), sharey=True)
    out = []
    for ax, (col, title) in zip(axes, panels):
        d = np.sort((df[col] - df["flow_z"]).to_numpy())
        rng = np.random.default_rng(0)
        reps = d[rng.integers(0, len(d), size=(4000, len(d)))].mean(axis=1)
        low, high = np.quantile(reps, [0.025, 0.975])
        out.append({"comparison": title, "mean": d.mean(), "low": low, "high": high,
                    "wins": int((d > 0).sum()), "clusters": len(d)})
        ax.axhline(0.0, color=INK["axis"], linewidth=1)
        ax.axhspan(low, high, color=SERIES[0], alpha=0.18)
        ax.axhline(d.mean(), color=SERIES[0], linewidth=2)
        ax.plot(np.arange(len(d)), d, "o", color=INK["secondary"], markersize=4.5)
        ax.set_title(title, fontweight="normal", fontsize=10)
        ax.set_xlabel("30 independent clusters, sorted by difference")
        ax.set_xticks([])
        ax.text(0.02, 0.95, f"mean {d.mean():+.3f}  [{low:+.3f}, {high:+.3f}]\nbetter on {int((d > 0).sum())} of {len(d)}",
                transform=ax.transAxes, va="top", fontsize=9, color=INK["primary"])
    axes[0].set_ylabel("difference in per-cluster PR-AUC")
    fig.suptitle("Real SKAB: per-cluster differences scatter far more than their mean (band = paired 95% interval)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    pd.DataFrame(out).to_csv(HERE / "paired_differences.csv", index=False)
    print(pd.DataFrame(out).round(4).to_string(index=False))
    save(fig, HERE / "paired_differences.svg")


def fig_wilson() -> None:
    cases = [(7, 9), (9, 9), (27, 34), (34, 34), (70, 90), (700, 900)]
    rows = []
    for k, n in cases:
        ci = binomtest(k, n).proportion_ci(method="wilson")
        rows.append({"k": k, "n": n, "rate": k / n, "low": ci.low, "high": ci.high})
    df = pd.DataFrame(rows)
    df.to_csv(HERE / "wilson_widths.csv", index=False)
    print(df.round(3).to_string(index=False))
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ypos = np.arange(len(df))[::-1]
    ax.hlines(ypos, df["low"], df["high"], color=SERIES[0], linewidth=5)
    ax.plot(df["rate"], ypos, "o", color=INK["primary"], markersize=5)
    for y, r in zip(ypos, df.itertuples()):
        ax.text(r.low - 0.012, y, f"{r.low:.2f}", ha="right", va="center", fontsize=8, color=INK["secondary"])
    ax.set_yticks(ypos, [f"{r.k} of {r.n}" for r in df.itertuples()])
    ax.set_xlim(0.36, 1.02)
    ax.set_ylim(-0.6, len(df) - 0.4)
    ax.set_xlabel("detection rate, Wilson 95% interval (number = lower limit)")
    ax.grid(axis="y", visible=False)
    ax.set_title("A handful of events says little: 9 of 9 still allows a 70% detector")
    save(fig, HERE / "wilson_widths.svg")


if __name__ == "__main__":
    for make in (fig_coverage, fig_skab_intervals, fig_paired_differences, fig_wilson):
        print(f"\n== {make.__name__}")
        make()
