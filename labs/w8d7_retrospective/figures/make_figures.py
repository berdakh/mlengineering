"""Regenerate the figure of lesson w8d7: which weeks produce evidence for which target capability.

    python labs/w8d7_retrospective/figures/make_figures.py

Parses the "What the course is for" table of ROADMAP.md (capability, evidence artifact, weeks) and
draws a capability-by-week grid. It shows where evidence *can* come from, not what you produced.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

text = (ROOT / "ROADMAP.md").read_text()
section = text.split("## What the course is for")[1].split("##")[0]
rows = []
for line in section.splitlines():
    m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+)\|\s*([^|]+)\|\s*([^|]+)\|", line)
    if m:
        num, cap, _, weeks = m.groups()
        ws = set()
        for part in weeks.split(","):
            part = part.strip()
            if "onward" in part:
                ws |= set(range(int(part.split()[0]), 9))
            elif "-" in part:
                a, b = part.split("-")
                ws |= set(range(int(a), int(b) + 1))
            elif part.isdigit():
                ws.add(int(part))
        rows.append((int(num), cap.strip(), sorted(ws)))
grid = np.zeros((len(rows), 8))
for i, (_, _, ws) in enumerate(rows):
    for w in ws:
        grid[i, w - 1] = 1
for num, cap, ws in rows:
    print(f"{num:2d} {cap[:48]:48s} weeks {ws}")

fig, ax = plt.subplots(figsize=(8.6, 3.8))
for i in range(len(rows)):
    for j in range(8):
        if grid[i, j]:
            ax.add_patch(plt.Rectangle((j + 0.08, i + 0.12), 0.84, 0.76, color=SERIES[0], lw=0))
ax.set_xlim(0, 8)
ax.set_ylim(len(rows), 0)
ax.set_xticks(np.arange(8) + 0.5, [f"W{w}" for w in range(1, 9)])
import textwrap
ax.set_yticks(np.arange(len(rows)) + 0.5, [f"{n}. " + textwrap.shorten(c, 46, placeholder=" ...") for n, c, _ in rows], fontsize=8)
ax.grid(False)
ax.tick_params(length=0)
ax.set_title("Where each target capability's evidence is produced (from ROADMAP.md)")
fig.text(0.01, 0.01, "A filled cell is an opportunity for evidence, not evidence. Your portfolio says what you produced.",
         fontsize=7.5, color=INK["muted"])
save(fig, HERE / "capability_weeks.svg")
print("wrote", HERE / "capability_weeks.svg")
