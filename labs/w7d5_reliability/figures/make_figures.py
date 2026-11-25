"""Figures for w7d5 (lesson and handbook H15.6). Regenerate from the repository root:

    python labs/w7d5_reliability/figures/make_figures.py

retry_storm.svg       SYNTHETIC: requests per 100 ms after an outage, exponential vs full-jitter retries
drill_latency.svg     REAL drill (solutions/.../drill_log/drill_log.json): p50/p95 latency per injected fault
fallback_vs_model.svg REAL SKAB test experiments: which faults the model and the fallback rule detect
Numbers plotted are also written to figure_data.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

DRILL = ROOT / "solutions" / "labs" / "w7d5_reliability" / "drill_log"
rows: list[dict] = []

# 1. retry storm (synthetic simulation from the worked example)
spec = importlib.util.spec_from_file_location("retry_storm", HERE.parent / "example" / "retry_storm.py")
storm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storm)
fig, axes = plt.subplots(2, 1, figsize=(7.2, 4.6), sharex=True, sharey=True)
for ax, (name, label, color) in zip(axes, [("exponential", "Exponential backoff, no jitter", SERIES[1]),
                                          ("full_jitter", "Exponential backoff with full jitter", SERIES[0])]):
    r = storm.simulate(name)
    buckets = sorted(r["load"])
    t = [b * storm.BUCKET_S for b in buckets]
    v = [r["load"][b] for b in buckets]
    ax.bar(t, v, width=storm.BUCKET_S * 0.9, color=color, align="edge")
    ax.axhline(storm.CAPACITY, color=INK["secondary"], lw=1, ls="--")
    ax.axvspan(0, storm.OUTAGE_S, color=INK["grid"], zorder=0)
    ax.set_title(f"{label}: {r['served']} of {storm.N_CLIENTS} served, {r['gave_up']} gave up", fontsize=10)
    ax.set_ylabel("requests / 100 ms")
    for b, n in zip(t, v):
        rows.append({"figure": "retry_storm", "series": name, "x": round(b, 2), "y": n})
axes[0].text(storm.OUTAGE_S + 0.1, storm.CAPACITY + 8, "capacity 20 per 100 ms", color=INK["secondary"], fontsize=8)
axes[0].text(0.6, 420, "service down", color=INK["secondary"], fontsize=8)
axes[1].set_xlabel("seconds since the outage began")
axes[1].set_xlim(0, 20)
fig.suptitle("Retries without jitter arrive in lock-step waves (SYNTHETIC simulation)", x=0.02, ha="left",
             fontweight="bold", fontsize=11)
save(fig, HERE / "retry_storm.svg")

# 2. drill latency
drill = json.loads((DRILL / "drill_log.json").read_text())
fig, ax = plt.subplots(figsize=(7.2, 3.4))
names = [d["name"] for d in drill][::-1]
p50 = [d["latency_ms"]["p50"] for d in drill][::-1]
p95 = [d["latency_ms"]["p95"] for d in drill][::-1]
y = range(len(names))
ax.barh([i + 0.2 for i in y], p50, height=0.38, color=SERIES[0], label="p50")
ax.barh([i - 0.2 for i in y], p95, height=0.38, color=SERIES[1], label="p95")
ax.set_yticks(list(y), names)
ax.set_xscale("log")
ax.set_xlabel("client-side latency per request, ms (log scale)")
ax.set_title("Deadline caps a slow model at ~250 ms; overload costs retries (REAL drill, valve1/13)")
ax.legend(loc="upper right")
for i, (a, b) in enumerate(zip(p50, p95)):
    ax.text(b * 1.15, i - 0.2, f"{b:.0f}", va="center", fontsize=8, color=INK["secondary"])
for d in drill:
    rows.append({"figure": "drill_latency", "series": d["name"], "x": "p50", "y": round(d["latency_ms"]["p50"], 1)})
    rows.append({"figure": "drill_latency", "series": d["name"], "x": "p95", "y": round(d["latency_ms"]["p95"], 1)})
save(fig, HERE / "drill_latency.svg")

# 3. fallback vs model
comp = json.loads((DRILL / "fallback_vs_model.json").read_text())
fig, ax = plt.subplots(figsize=(6.4, 3.4))
exps = [r["experiment_id"] for r in comp["per_experiment"]]
for j, (name, color) in enumerate([("model", SERIES[0]), ("fallback", SERIES[1])]):
    for i, r in enumerate(comp["per_experiment"]):
        hit = r[name]["detected"]
        ax.scatter(j, i, s=220, color=color if hit else INK["surface"], edgecolor=color, linewidth=2, zorder=3)
        rows.append({"figure": "fallback_vs_model", "series": name, "x": r["experiment_id"], "y": int(hit)})
ax.set_yticks(range(len(exps)), exps)
s = comp["summary"]
ax.set_xticks([0, 1], [f"model\n{s['model']['faults_detected']}/7 detected", f"fallback rule\n{s['fallback']['faults_detected']}/7 detected"])
ax.set_xlim(-0.6, 1.6)
ax.invert_yaxis()
ax.grid(False)
ax.set_title("Degraded mode is worse: the envelope rule catches 2 of 7 test faults (REAL SKAB)")
ax.text(1.65, len(exps) - 0.5, "filled = fault detected\nhollow = missed\nfalse alarms: 0 for both", fontsize=8,
        color=INK["secondary"], va="bottom")
save(fig, HERE / "fallback_vs_model.svg")

with (HERE / "figure_data.csv").open("w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
    w.writeheader()
    w.writerows(rows)
print("wrote retry_storm.svg, drill_latency.svg, fallback_vs_model.svg, figure_data.csv")
