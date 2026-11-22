"""Figures for w2d3 and handbook H3.3 / H4.1, computed from the REAL SKAB files.

    python project/get_skab.py        # once
    python lessons/w2d3_data_quality_ingestion/figures/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "lessons" / "w2d3_data_quality_ingestion" / "lab" / "src"))

RAW = ROOT / "data" / "raw" / "skab"
if not RAW.is_dir():
    sys.exit("data/raw/skab not found. Run:  python project/get_skab.py")

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FAMILY_COLOUR = {"valve1": SERIES[0], "valve2": SERIES[1], "other": SERIES[2], "anomaly-free": SERIES[3]}


def experiment_order(tidy):
    fam_rank = {"valve1": 0, "valve2": 1, "other": 2}
    ids = tidy.loc[tidy.family != "anomaly-free", ["experiment_id", "family"]].drop_duplicates()
    ids["n"] = ids.experiment_id.str.split("/").str[1].astype(int)
    return ids.sort_values(by=["family", "n"], key=lambda s: s.map(fam_rank) if s.name == "family" else s)


def main() -> None:
    tidy = load_raw(RAW).sort_values(["experiment_id", "datetime"])
    tidy["elapsed_s"] = (tidy.datetime - tidy.groupby("experiment_id").datetime.transform("min")).dt.total_seconds()
    tidy["step_s"] = tidy.groupby("experiment_id").datetime.diff().dt.total_seconds()

    # Figure 1: every labelled experiment on a common elapsed-time axis
    order = experiment_order(tidy)
    fig, ax = plt.subplots(figsize=(8, 7.2))
    n_gaps = 0
    for y, row in enumerate(order.itertuples()):
        g = tidy[tidy.experiment_id == row.experiment_id]
        ax.hlines(y, 0, g.elapsed_s.max(), color=INK["axis"], linewidth=5)
        a = g[g.anomaly == 1]
        ax.hlines(y, a.elapsed_s.min(), a.elapsed_s.max(), color=SERIES[1], linewidth=5,
                  label="labelled anomalous segment" if y == 0 else None)
        big = g[g.step_s > 5]
        n_gaps += len(big)
        ax.scatter(big.elapsed_s - big.step_s / 2, [y] * len(big), marker="|", s=160, color=INK["primary"],
                   linewidth=1.6, zorder=3, label="sampling gap > 5 s" if (len(big) and n_gaps == len(big)) else None)
    ax.hlines([], 0, 0, color=INK["axis"], linewidth=5, label="normal operation")
    ax.set_yticks(range(len(order)), order.experiment_id, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("elapsed time since the first sample of the experiment (s)")
    ax.set_title("34 labelled SKAB experiments: one anomalous segment each,\nstarting at almost the same elapsed time (real data)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=3)
    save(fig, HERE / "experiment_timelines.svg")
    starts = tidy[tidy.anomaly == 1].groupby("experiment_id").t.min()
    print(f"experiments {len(order)}; gaps > 5 s plotted {n_gaps} in {tidy[tidy.step_s > 5].experiment_id.nunique()} files")
    print(f"anomaly start row: median {starts.median():.0f}, in [550, 600] for {(starts.between(550, 600)).sum()} of {len(starts)}")

    # Figure 2: sensor levels during NORMAL operation, by family (small multiples)
    normal = tidy[tidy.anomaly == 0]
    fams = ["valve1", "valve2", "other", "anomaly-free"]
    fig, axes = plt.subplots(2, 4, figsize=(9.5, 4.8))
    print("\nmedian sensor value on normal rows, by family")
    print(normal.groupby("family")[list(SENSOR_COLUMNS)].median().loc[fams].round(3).to_string())
    for ax, col in zip(axes.ravel(), SENSOR_COLUMNS):
        data = [normal.loc[normal.family == f, col].to_numpy() for f in fams]
        bp = ax.boxplot(data, widths=0.55, patch_artist=True, showfliers=False,
                        medianprops={"color": INK["primary"], "linewidth": 1.2},
                        whiskerprops={"color": INK["muted"]}, capprops={"color": INK["muted"]})
        for patch, f in zip(bp["boxes"], fams):
            patch.set_facecolor(FAMILY_COLOUR[f])
        ax.set_title(col, fontsize=9, fontweight="normal")
        ax.set_xticks(range(1, 5), ["v1", "v2", "oth", "free"], fontsize=8)
        ax.grid(axis="x", visible=False)
    fig.suptitle("Two operating regimes: valve experiments run at a quarter of the flow of the 'other' family\n"
                 "and of the fault-free recording (real data, normal rows only; boxes = quartiles, outliers hidden)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.text(0.01, -0.02, "v1 = valve1, v2 = valve2, oth = other, free = anomaly-free recording. Units as in the data dictionary.",
             color=INK["secondary"], fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, HERE / "sensor_levels_by_family.svg")
    _ = np


if __name__ == "__main__":
    main()
