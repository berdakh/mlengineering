"""Figures for the reference technical report, from results.json only.

    python solutions/lessons/w8d2_report_limitations/reference/make_figures.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

res = json.loads((HERE / "results.json").read_text())

# Figure 1: test PR-AUC with cluster-bootstrap intervals, one look, operating points from development data.
fig, ax = plt.subplots(figsize=(7.2, 2.9))
rows = res["test"]
names = [r["name"] for r in rows]
for i, r in enumerate(rows):
    color = SERIES[0] if r["chosen"] else INK["muted"]
    ax.plot([r["pr_auc_lo"], r["pr_auc_hi"]], [i, i], color=color, lw=2.5, solid_capstyle="round")
    ax.plot(r["pr_auc"], i, "o", color=color, ms=7, mec=INK["surface"], mew=1.5)
    ax.text(r["pr_auc_hi"] + 0.012, i, f"{r['pr_auc']:.3f}  ({r['events_detected']} of {r['events_total']} faults)",
            va="center", fontsize=9, color=INK["secondary"])
ax.axvline(res["data"]["anomalous_row_fraction"], color=INK["axis"], lw=1, ls="--")
ax.text(res["data"]["anomalous_row_fraction"] + 0.008, 2.5, "no-skill floor", fontsize=8, color=INK["muted"])
ax.set_yticks(range(len(rows)), names)
ax.invert_yaxis()
ax.set_xlim(0.3, 1.12)
ax.set_xlabel("Test PR-AUC (7 experiments; 95 % cluster bootstrap over overlap groups)")
ax.set_title("Chosen detector (blue) on the single test look; other candidates recorded only")
ax.grid(axis="y", visible=False)
save(fig, HERE / "figures" / "test_intervals.svg")

# Figure 2: protocol A (frozen test) versus protocol B (unseen fault family), same detectors.
fig, ax = plt.subplots(figsize=(7.2, 2.9))
labels = {"gbt": "gradient-boosted trees", "flow": "flow-rate |z|", "iforest": "isolation forest", "pca_t2": "PCA T²"}
order = ["gbt", "flow", "iforest", "pca_t2"]
for i, k in enumerate(order):
    a, b = res["protocol_b"][k]["a"], res["protocol_b"][k]["b"]
    ax.annotate("", xy=(b, i), xytext=(a, i), arrowprops=dict(arrowstyle="->", color=INK["muted"], lw=1.2))
    ax.plot(a, i, "o", color=SERIES[0], ms=7, mec=INK["surface"], mew=1.5, label="A: frozen test" if i == 0 else None)
    ax.plot(b, i, "o", color=SERIES[1], ms=7, mec=INK["surface"], mew=1.5, label="B: unseen family" if i == 0 else None)
    ax.text(max(a, b) + 0.012, i, f"{a:.3f} → {b:.3f}", va="center", fontsize=9, color=INK["secondary"])
ax.set_yticks(range(len(order)), [labels[k] for k in order])
ax.invert_yaxis()
ax.set_xlim(0.55, 1.05)
ax.set_xlabel("PR-AUC")
ax.set_title("The two best detectors on A lose the most on an unseen fault family")
ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncols=2)
ax.grid(axis="y", visible=False)
save(fig, HERE / "figures" / "protocol_a_vs_b.svg")
print("wrote figures/test_intervals.svg, figures/protocol_a_vs_b.svg")
