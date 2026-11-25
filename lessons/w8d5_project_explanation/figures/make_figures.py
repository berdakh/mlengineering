"""Regenerate the figures of lesson w8d5.

    python lessons/w8d5_project_explanation/figures/make_figures.py

Figure 1 runs example/script_lint.py on the reference 5-minute script (solutions tree) and plots the
speaking time per section. Figure 2 plots the committed REAL SKAB decision table of w4d5
(lessons/w4d5_model_choice/figures/decision_table.csv and test_look.csv): the "one results table"
of the walkthrough, as a picture. matplotlib is needed only here.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE.parent / "example")]
from script_lint import lint  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

# ---------------------------------------------------------------- figure 1: speaking time
script = ROOT / "solutions" / "lessons" / "w8d5_project_explanation" / "lab" / "WALKTHROUGH_5MIN.md"
rows, _ = lint(script.read_text())
print("section, words, seconds")
for h, n, s in rows:
    print(f"  {h:12s} {n:4d} {s:5.0f}")
fig, ax = plt.subplots(figsize=(7.2, 2.8))
names = [r[0] for r in rows][::-1]
secs = [r[2] for r in rows][::-1]
ax.barh(range(len(rows)), secs, color=SERIES[0], height=0.6)
for i, s in enumerate(secs):
    ax.text(s + 1.5, i, f"{s:.0f} s", va="center", fontsize=8.5, color=INK["secondary"])
ax.axvline(90, color=INK["muted"], lw=1, ls="--")
ax.text(91, len(rows) - 0.6, "90 s: the listener's limit", fontsize=7.5, color=INK["muted"])
ax.set_yticks(range(len(rows)), names)
ax.set_xlim(0, 115)
ax.set_xlabel("seconds at 140 words per minute")
ax.set_title(f"Reference 5-minute script: {sum(r[1] for r in rows)} words, about {sum(secs) / 60:.1f} min")
save(fig, HERE / "speaking_time.svg")

# ---------------------------------------------------------------- figure 2: the one results table
dev = pd.read_csv(ROOT / "lessons" / "w4d5_model_choice" / "figures" / "decision_table.csv")
test = pd.read_csv(ROOT / "lessons" / "w4d5_model_choice" / "figures" / "test_look.csv")
dev = dev.merge(test[["name", "events"]].rename(columns={"events": "test_events"}), on="name")
print(dev[["name", "primary", "primary_lo", "primary_hi", "test_events", "size_bytes"]].round(3).to_string(index=False))
fig, ax = plt.subplots(figsize=(7.2, 2.9))
order = dev.sort_values("primary").reset_index(drop=True)
for i, r in order.iterrows():
    chosen = r["name"] == "flow-rate |z|"
    color = SERIES[0] if chosen else INK["muted"]
    ax.plot([r.primary_lo, r.primary_hi], [i, i], color=color, lw=2.5, solid_capstyle="round")
    ax.plot(r.primary, i, "o", color=color, ms=8, mec=INK["surface"], mew=2)
    ax.text(0.97, i, f"test: {r.test_events} faults   {int(r.size_bytes):,} B", va="center", fontsize=8,
            color=INK["secondary"], transform=ax.get_yaxis_transform(), ha="right")
ax.set_yticks(range(len(order)), [n + ("  (chosen)" if n == "flow-rate |z|" else "") for n in order["name"]])
ax.set_xlim(0.4, 1.25)
ax.set_xlabel("development PR-AUC with 95 % interval (experiment bootstrap)")
ax.set_title("The one results slide: overlapping intervals, very different costs (REAL SKAB)")
save(fig, HERE / "results_slide.svg")
print("wrote speaking_time.svg, results_slide.svg")
