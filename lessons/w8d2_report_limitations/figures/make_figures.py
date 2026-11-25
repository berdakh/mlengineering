"""Figures for w8d2. Run from the repository root:

    python lessons/w8d2_report_limitations/figures/make_figures.py

1. wilson_width.svg: computed. Width of the 95 % Wilson interval for a recall of 5/7, as the number of
   test events grows; marks the 7 test events and the 34 events of the whole data set.
2. overlap_vs_paired.svg: REAL. Test PR-AUC of the chosen detector and the logistic model with their
   cluster-bootstrap intervals (from the committed w4d6 results.json), next to the development-set paired
   difference and its interval. Overlapping intervals do not answer "which is better".
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402


def wilson(k: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


rows = []
ns = list(range(5, 201))
widths = []
for n in ns:
    lo, hi = wilson(5 / 7 * n, n)
    widths.append(hi - lo)
    rows.append(["wilson_width", n, f"{hi - lo:.4f}"])
fig, ax = plt.subplots(figsize=(7.2, 3.0))
ax.plot(ns, widths, color=SERIES[0])
for n, label in ((7, "7 test events"), (34, "34 events in all of SKAB")):
    lo, hi = wilson(5 / 7 * n, n)
    ax.plot(n, hi - lo, "o", color=SERIES[1], ms=7, mec=INK["surface"], mew=1.5)
    ax.annotate(f"{label}: [{lo:.2f}, {hi:.2f}]", (n, hi - lo), xytext=(14, 6), textcoords="offset points",
                fontsize=9, color=INK["secondary"])
ax.set_xlabel("number of fault events evaluated")
ax.set_ylabel("width of 95 % interval")
ax.set_ylim(0, 0.65)
ax.set_title("Recall of 5 of 7: the interval is 0.56 wide; even 200 events leave it 0.12 wide")
save(fig, HERE / "wilson_width.svg")

res = json.loads((ROOT / "solutions/lessons/w4d6_project_milestone_1/example_report/results.json").read_text())
test = {t["name"]: t for t in res["test"]}
dev = {d["name"]: d for d in res["development"]}
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw={"width_ratios": [1.3, 1]})
for i, (name, color) in enumerate((("flow-rate |z|", SERIES[0]), ("logistic (supervised)", SERIES[2]))):
    t = test[name]
    ax1.plot([t["pr_auc_lo"], t["pr_auc_hi"]], [i, i], color=color, lw=2.5, solid_capstyle="round")
    ax1.plot(t["pr_auc"], i, "o", color=color, ms=7, mec=INK["surface"], mew=1.5)
    ax1.text(t["pr_auc_hi"] + 0.006, i, f"{t['pr_auc']:.3f}", va="center", fontsize=9, color=INK["secondary"])
    rows.append(["overlap_vs_paired", f"test {name}", f"{t['pr_auc']:.4f} [{t['pr_auc_lo']:.4f}, {t['pr_auc_hi']:.4f}]"])
ax1.set_yticks([0, 1], ["flow-rate |z|", "logistic"])
ax1.set_ylim(1.6, -0.6)
ax1.set_xlim(0.78, 0.99)
ax1.set_xlabel("test PR-AUC, separate intervals")
ax1.set_title("Separate intervals overlap")
ax1.grid(axis="y", visible=False)
d = dev["logistic (supervised)"]
ax2.axvspan(-res["protocol"]["mpid"], res["protocol"]["mpid"], color=INK["grid"], lw=0)
ax2.axvline(0, color=INK["axis"], lw=1)
ax2.plot([d["diff_lo"], d["diff_hi"]], [0, 0], color=SERIES[2], lw=2.5, solid_capstyle="round")
ax2.plot(d["diff"], 0, "o", color=SERIES[2], ms=7, mec=INK["surface"], mew=1.5)
ax2.text(d["diff"], -0.35, f"+{d['diff']:.3f} [{d['diff_lo']:.3f}, {d['diff_hi']:.3f}]", ha="center",
         fontsize=9, color=INK["secondary"])
ax2.text(0, 0.42, f"±{res['protocol']['mpid']} MPID band", ha="center", fontsize=8, color=INK["muted"])
rows.append(["overlap_vs_paired", "dev paired diff logistic - flow", f"{d['diff']:.4f} [{d['diff_lo']:.4f}, {d['diff_hi']:.4f}]"])
ax2.set_yticks([])
ax2.set_ylim(0.7, -0.7)
ax2.set_xlim(-0.08, 0.16)
ax2.set_xlabel("development, paired difference")
ax2.set_title("Paired: excludes 0, not the band")
ax2.grid(axis="y", visible=False)
save(fig, HERE / "overlap_vs_paired.svg")

with open(HERE / "figure_data.csv", "w", newline="") as fh:
    csv.writer(fh).writerows([["figure", "item", "value"]] + rows)
print("wrote wilson_width.svg, overlap_vs_paired.svg, figure_data.csv")
