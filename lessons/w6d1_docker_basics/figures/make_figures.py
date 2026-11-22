"""Regenerate the data figures of lesson w6d1 from measurements.json.

    python lessons/w6d1_docker_basics/figures/make_figures.py

The measurements need a Docker daemon and were taken once (see the _provenance field and the
lesson, section 3); this script only draws them, so it runs anywhere. To re-measure on your
machine, repeat the commands in the lesson and edit measurements.json.
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

M = json.loads((HERE / "measurements.json").read_text())


def dot_bars(ax, data: dict, unit: str, color: str, xmax: float):
    labels = list(data)
    means = [float(np.mean(v)) for v in data.values()]
    y = np.arange(len(labels))[::-1]
    ax.barh(y, means, color=color, height=0.55)
    for yi, values in zip(y, data.values()):
        ax.scatter(values, [yi] * len(values), s=14, color=INK["primary"], zorder=3)
        ax.text(max(values) + 0.035 * xmax, yi, f"{np.mean(values):.1f} {unit}", va="center", color=INK["secondary"], fontsize=9)
    ax.set_yticks(y, labels)
    ax.grid(axis="y", visible=False)


# 1 ------------------------------------------------------------------ docker stop time
fig, ax = plt.subplots(figsize=(7.4, 2.9))
dot_bars(ax, M["stop_seconds"], "s", SERIES[0], 13.5)
ax.axvline(10, color=INK["muted"], linewidth=1, linestyle="--")
ax.text(9.9, 2.5, "10 s grace\nperiod, then\nSIGKILL", color=INK["muted"], fontsize=8, va="center", ha="right")
ax.set_xlabel("time for `docker stop` to return (s); dots = 3 runs")
ax.set_xlim(0, 13.5)
ax.set_title("Shell-form CMD makes every stop wait for SIGKILL")
save(fig, HERE / "stop_time.svg")

# 2 ------------------------------------------------------------------ rebuild after a code edit
fig, ax = plt.subplots(figsize=(7.4, 2.0))
dot_bars(ax, M["rebuild_after_code_edit_seconds"], "s", SERIES[0], 25)
ax.set_xlabel("rebuild time after editing one line of src/ (s); dots = 3 runs")
ax.set_xlim(0, 25)
ax.set_title("Layer order decides whether a code edit reinstalls numpy and pandas")
save(fig, HERE / "rebuild_time.svg")

# 3 ------------------------------------------------------------------ what the image is made of
layers = M["image_layers_mb"]
fig, ax = plt.subplots(figsize=(7.4, 2.8))
names = list(layers)[::-1]
values = [layers[n] for n in names]
ax.barh(names, values, color=SERIES[0], height=0.55)
for i, v in enumerate(values):
    ax.text(v + 3, i, f"{v:,.0f} MB" if v >= 1 else f"{v * 1000:,.0f} kB", va="center", color=INK["secondary"], fontsize=9)
ax.set_xlim(0, 215)
ax.set_xlabel("layer size on disk (MB), from `docker history`")
ax.set_title(f"The {M['image_disk_mb']} MB image is base + dependencies; your code is kilobytes")
ax.grid(axis="y", visible=False)
save(fig, HERE / "image_layers.svg")

# 4 ------------------------------------------------------------------ .dockerignore and COPY . .
ctx = M["context_experiment"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.5))
cases = list(ctx["context_sent_mb"])
for ax, key, unit, title in ((axes[0], "context_sent_mb", "MB", "build context sent"),
                             (axes[1], "image_content_mb", "MB", "image content (compressed, as pushed)")):
    vals = [ctx[key][c] for c in cases]
    ax.barh(cases[::-1], vals[::-1], color=SERIES[0], height=0.5)
    for i, v in enumerate(vals[::-1]):
        ax.text(v + max(vals) * 0.02, i, f"{v:,.0f} {unit}" if v >= 1 else f"{v * 1000:.1f} kB",
                va="center", color=INK["secondary"], fontsize=9)
    ax.set_xlim(0, max(vals) * 1.35)
    ax.set_title(title, fontsize=10, fontweight="normal")
    ax.grid(axis="y", visible=False)
axes[1].set_yticks([])
fig.suptitle("With COPY . . a missing .dockerignore ships the local junk inside the image",
             x=0.01, ha="left", fontweight="bold", fontsize=11)
fig.tight_layout()
save(fig, HERE / "dockerignore_effect.svg")

for key in ("stop_seconds", "rebuild_after_code_edit_seconds"):
    for label, values in M[key].items():
        print(f"{key:34s} {label:38s} mean {np.mean(values):6.2f}  runs {values}")
print("wrote stop_time.svg, rebuild_time.svg, image_layers.svg, dockerignore_effect.svg")
