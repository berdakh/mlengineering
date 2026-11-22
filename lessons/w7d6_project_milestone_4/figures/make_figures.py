"""Figures for w7d6. Regenerate from the repository root (needs the SKAB files: python project/get_skab.py):

    python lessons/w7d6_project_milestone_4/figures/make_figures.py

demo_signals.svg      REAL: monitoring signals per event of the reference demo
                      (solutions/lessons/w7d6_project_milestone_4/example_demo/results.json)
drift_calibration.svg REAL: PSI of each development experiment's normal rows (the calibration set) against
                      the threshold, with the demo's replays and the healthy test experiment closest to it
Numbers plotted are also written to figure_data.csv.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOL = ROOT / "solutions" / "lessons" / "w7d6_project_milestone_4"
sys.path[:0] = [str(ROOT), str(SOL / "lab" / "src")]
from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.data import load_raw  # noqa: E402
from flowguard.monitoring import DriftMonitor  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

rows: list[dict] = []
res = json.loads((SOL / "example_demo" / "results.json").read_text())

# 1. signals per event
evs = [e for e in res["events"] if "values" in e["observed"]]
names = [e["id"] for e in evs]
panels = [("Alarm rate", [e["observed"]["alarm_rate"] for e in evs], res["alarm_rate_budget"], "budget 0.05"),
          ("Drift PSI", [e["observed"]["psi"] for e in evs], res["drift_threshold"],
           f"threshold {res['drift_threshold']:.2f}"),
          ("Out-of-support share", [e["observed"]["out_of_support_values"] / e["observed"]["values"] for e in evs],
           None, "")]
fig, axes = plt.subplots(3, 1, figsize=(7.4, 6.2), sharex=True)
for ax, (title, vals, limit, label) in zip(axes, panels):
    colors = [SERIES[1] if (limit is not None and v > limit) or (limit is None and v > 0) else SERIES[0] for v in vals]
    ax.bar(range(len(vals)), vals, color=colors, width=0.6)
    if limit is not None:
        ax.axhline(limit, color=INK["secondary"], lw=1, ls="--")
        ax.text(-0.45, limit, f" {label}", color=INK["secondary"], fontsize=8, va="bottom")
    ax.set_ylabel(title, fontsize=9)
    for n, v in zip(names, vals):
        rows.append({"figure": "demo_signals", "series": title, "x": n, "y": round(v, 4)})
axes[-1].set_xticks(range(len(names)), names, rotation=20, ha="right")
axes[0].set_title("Each scripted problem raises its own signal; normal operation raises none (REAL demo)")
axes[0].text(len(names) - 0.6, 0.27, "orange = above its alert line", ha="right", fontsize=8, color=INK["secondary"])
save(fig, HERE / "demo_signals.svg")

# 2. drift calibration
tidy = load_raw(ROOT / "data" / "raw" / "skab")
manifest = load_splits(SOL / "lab" / "splits" / "v2.json")
dev = tidy[tidy["experiment_id"].isin(set(dev_experiments(manifest)))]
nd = dev[dev["anomaly"] == 0]
windows = {k: g["flow_rate"].to_numpy(dtype=float) for k, g in nd.groupby("experiment_id")}
mon = DriftMonitor.calibrate(nd["flow_rate"].to_numpy(dtype=float), list(windows.values()))
cal = sorted(((mon.check(w)[0], k) for k, w in windows.items()))
other1 = tidy[tidy["experiment_id"] == "other/1"].sort_values("t")
x1 = other1["flow_rate"].to_numpy(dtype=float)[: int(np.argmax(other1["anomaly"].to_numpy()))]
probe = [("E1-normal (valve1/5)", next(e["observed"]["psi"] for e in evs if e["id"] == "E1-normal")),
         ("other/1, healthy part", mon.check(x1)[0]),
         ("E3-input-drift (x0.8)", next(e["observed"]["psi"] for e in evs if e["id"] == "E3-input-drift"))]
fig, ax = plt.subplots(figsize=(7.4, 3.4))
ax.scatter([v for v, _ in cal], [0] * len(cal), s=60, color=SERIES[0], alpha=0.7, label="development experiments (calibration)")
for i, (name, v) in enumerate(probe):
    color = SERIES[1] if v > mon.threshold else SERIES[2]
    ax.scatter([v], [1 + i * 0.5], s=80, color=color, marker="D")
    ax.text(v, 1.18 + i * 0.5, f"{name}: {v:.2f}", fontsize=8, ha="center", color=INK["secondary"])
    rows.append({"figure": "drift_calibration", "series": "probe", "x": name, "y": round(v, 4)})
for v, k in cal:
    rows.append({"figure": "drift_calibration", "series": "calibration", "x": k, "y": round(v, 4)})
ax.axvline(mon.threshold, color=STATUS["critical"], lw=1.2, ls="--")
ax.text(mon.threshold, -0.45, f" threshold = max = {mon.threshold:.2f}", color=STATUS["critical"], fontsize=8)
ax.set_yticks([0, 1, 1.5, 2], ["calibration", "", "", ""])
ax.set_ylim(-0.6, 2.6)
ax.set_xlabel("PSI of flow rate against the pooled development reference")
ax.set_title("Healthy experiments already differ a lot from the pooled reference (REAL SKAB)")
ax.legend(loc="upper left", fontsize=8)
save(fig, HERE / "drift_calibration.svg")

with (HERE / "figure_data.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
    w.writeheader()
    w.writerows(rows)
print(f"threshold {mon.threshold:.4f}; calibration PSI {cal[0][0]:.3f}..{cal[-1][0]:.3f}; "
      + "; ".join(f"{n} {v:.3f}" for n, v in probe))
