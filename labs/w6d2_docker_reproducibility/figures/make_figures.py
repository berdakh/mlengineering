"""Regenerate the data figures of lesson w6d2 from measurements.json.

    python labs/w6d2_docker_reproducibility/figures/make_figures.py

The measurements need Docker and network access and were taken once (see _provenance and the
lesson); this script only draws them. The resolved versions come from
example/resolve_on_two_dates.py, whose output is copied in the lesson.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

M = json.loads((HERE / "measurements.json").read_text())

# 1 ------------------------------------------------------------------ image sizes: base vs added
images = M["images"]
names = list(images)[::-1]
fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.0), sharey=True)
for ax, total_key, base_key, title in ((axes[0], "disk_mb", "base_disk_mb", "on disk (MB)"),
                                       (axes[1], "content_mb", "base_content_mb", "compressed, as pushed (MB)")):
    base = np.array([images[n][base_key] for n in names])
    added = np.array([images[n][total_key] for n in names]) - base
    ax.barh(names, base, color=SERIES[0], height=0.55)
    ax.barh(names, added, left=base + max(base) * 0.004, color=SERIES[1], height=0.55)
    for i, n in enumerate(names):
        ax.text(images[n][total_key] + max(base) * 0.03, i, f"{images[n][total_key]:,.0f}", va="center",
                color=INK["secondary"], fontsize=9)
    ax.set_xlim(0, max(images[n][total_key] for n in names) * 1.25)
    ax.set_title(title, fontsize=10, fontweight="normal")
    ax.grid(axis="y", visible=False)
fig.legend(handles=[Patch(color=SERIES[0], label="base image"), Patch(color=SERIES[1], label="added by the Dockerfile")],
           loc="lower center", ncol=2, fontsize=8, bbox_to_anchor=(0.6, -0.04))
fig.suptitle("The base image decides the size; multi-stage saves nothing here", x=0.01, ha="left",
             fontweight="bold", fontsize=11)
fig.tight_layout()
save(fig, HERE / "image_sizes.svg")

# 2 ------------------------------------------------------------------ what the dependencies weigh
sp = M["site_packages_kb_w6d2"]
labels = list(sp)[::-1]
values = np.array([sp[k] for k in labels]) / 1000
fig, ax = plt.subplots(figsize=(7.4, 3.3))
ax.barh(labels, values, color=SERIES[0], height=0.6)
for i, v in enumerate(values):
    ax.text(v + 1, i, f"{v:,.1f} MB", va="center", color=INK["secondary"], fontsize=9)
ax.set_xlim(0, values.max() * 1.18)
ax.set_xlabel("installed size in /opt/venv (MB, du)")
ax.set_title(f"pandas and numpy are {100 * (sp['pandas'] + sp['numpy (incl. numpy.libs)']) / sum(sp.values()):.0f}% "
             f"of the {sum(sp.values()) / 1000:.0f} MB of dependencies")
ax.grid(axis="y", visible=False)
save(fig, HERE / "dependency_sizes.svg")

# 3 ------------------------------------------------------------------ same requirements.in, three dates
rows = M["resolved_versions"]
dates = M["resolution_dates"]
fig, ax = plt.subplots(figsize=(7.4, 5.2))
for y, (name, *versions) in enumerate(rows[::-1]):
    today = versions[-1]
    for x, v in enumerate(versions):
        differs = v != today
        ax.scatter(x, y, s=60, color=SERIES[1] if differs else INK["grid"], zorder=3,
                   edgecolor=INK["surface"], linewidth=1)
        ax.text(x + 0.09, y, v, va="center", fontsize=7.5, color=INK["primary"] if differs else INK["muted"])
ax.set_yticks(range(len(rows)), [r[0] for r in rows[::-1]], fontsize=8)
ax.set_xticks(range(len(dates)), [f"resolved {d}" + (" (today)" if i == len(dates) - 1 else "") for i, d in enumerate(dates)],
              fontsize=8)
ax.set_xlim(-0.3, len(dates) - 0.2)
ax.grid(False)
ax.legend(handles=[Patch(color=SERIES[1], label="differs from today's resolution"),
                   Patch(color=INK["grid"], label="same as today (or absent: '-')")],
          loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=2, fontsize=8)
ax.set_title("One unchanged requirements.in, three different environments")
save(fig, HERE / "resolution_drift.svg")

changed_2w = [r[0] for r in rows if r[2] != r[3]]
changed_1y = [r[0] for r in rows if r[1] != r[3]]
print(f"two weeks: {len(changed_2w)} packages differ {changed_2w}")
print(f"one year:  {len(changed_1y)} packages differ")
print("wrote image_sizes.svg, dependency_sizes.svg, resolution_drift.svg")
