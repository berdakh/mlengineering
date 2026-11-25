"""Regenerate the figure of the w8d6 README (time budget per section and sitting).

    python lessons/w8d6_final_assessment/figures/make_figures.py

The numbers are the time boxes stated in the section READMEs (planning values, not measurements).
matplotlib is needed only here.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

SITTINGS = {  # (section, minutes)
    "A": [("f1 Python", 40), ("f2 SQL", 35), ("f3 cleaning", 35)],
    "B": [("f4 baseline", 35), ("f5 leakage", 35), ("f6 tests/API", 25), ("f7 memo", 20)],
    "T": [("t1 transfer", 90), ("report", 10)],
}
COLORS = {"A": SERIES[0], "B": SERIES[1], "T": SERIES[2]}

fig, ax = plt.subplots(figsize=(7.2, 2.6))
for row, (sitting, parts) in enumerate(SITTINGS.items()):
    left = 0
    for name, minutes in parts:
        ax.barh(row, minutes - 2, left=left + 1, color=COLORS[sitting], height=0.6)
        ax.text(left + minutes / 2, row, f"{name}\n{minutes}", ha="center", va="center",
                fontsize=7.5, color="#ffffff" if sitting != "T" else INK["primary"])
        left += minutes
    ax.text(left + 3, row, f"{left} min", va="center", fontsize=9, color=INK["secondary"])
    print(sitting, left)
ax.set_yticks(range(3), ["Sitting A", "Sitting B", "Sitting T"])
ax.invert_yaxis()
ax.set_xlim(0, 135)
ax.set_xlabel("minutes (time boxes, not measurements)")
ax.set_title("Three sittings: A and B mirror the Week 1 diagnostic; T is new")
ax.grid(axis="y", visible=False)
save(fig, HERE / "time_budget.svg")
print("wrote", HERE / "time_budget.svg")
