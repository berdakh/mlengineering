"""Regenerate the data figures of lesson w6d5 from committed CSVs (no Docker, no AWS needed).

    python lessons/w6d5_cloud_deployment/figures/make_figures.py

Inputs (written by the author-side recorder
solutions/lessons/w6d5_cloud_deployment/record/record_local.py, which runs Docker):
  startup_runs.csv  - 5 local runs of the image with the task definition's settings
  image_layers.csv  - `docker history` of the image
The billed-units figure is arithmetic (example/task_hours.py), not prices.
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(HERE.parent / "example")]

from tools.figstyle import INK, SEQUENTIAL, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from task_hours import HOURS_PER_MONTH, SCENARIOS, units  # noqa: E402


def startup() -> None:
    rows = list(csv.DictReader(open(HERE / "startup_runs.csv")))
    fig, ax = plt.subplots(figsize=(7, 3.2))
    marks = [("healthz_s", "/healthz 200 (process up)", SERIES[0], "o", 90),
             ("readyz_s", "/readyz 200 (model loaded)", SERIES[1], "D", 26),
             ("healthy_s", "Docker health: healthy", SERIES[2], "o", 48)]
    for i, r in enumerate(rows):
        y = len(rows) - i
        for key, label, colour, marker, size in marks:
            ax.scatter(float(r[key]), y, color=colour, marker=marker, s=size, zorder=3, label=label if i == 0 else None)
        ax.plot([0, float(r["healthy_s"])], [y, y], color=INK["grid"], lw=2, zorder=1)
    ax.set_yticks(range(1, len(rows) + 1), [f"run {len(rows) - i}" for i in range(len(rows))])
    ax.set_xlabel("seconds after docker run")
    ax.set_xlim(0, 7)
    ax.set_ylim(0.4, len(rows) + 1.6)
    ax.legend(loc="upper left", ncols=3, fontsize=8)
    ax.set_title("The container serves in about 3 s; Docker calls it healthy after the next check")
    save(fig, HERE / "startup_timeline.svg")


def _bytes(size: str) -> float:
    m = re.fullmatch(r"([\d.]+)([kMG]?B)", size)
    return float(m.group(1)) * {"B": 1, "kB": 1e3, "MB": 1e6, "GB": 1e9}[m.group(2)]


def layers() -> None:
    rows = [r for r in csv.DictReader(open(HERE / "image_layers.csv")) if _bytes(r["size"]) > 0]
    def label(cmd: str) -> str:
        if cmd.startswith("# debian"):
            return "base OS (debian slim)"
        if "apt-get install" in cmd and "ca" in cmd:
            return "base: CA certificates etc."
        if "savedAptMark" in cmd:
            return "base: Python 3.12 build"
        if "pip install" in cmd:
            return "RUN pip install (dependencies)"
        if cmd.startswith("COPY wheels"):
            return "COPY wheels/ (left in a layer)"
        if "useradd" in cmd:
            return "RUN useradd app (non-root user)"
        if "for src in idle3" in cmd:
            return "base: python3 symlinks"
        return cmd.split(" # ")[0][:34]
    data = sorted(((label(r["created_by"]), _bytes(r["size"]) / 1e6) for r in rows), key=lambda x: x[1])
    data = [d for d in data if d[1] >= 0.01]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    names, mb = zip(*data)
    colours = [SERIES[1] if "wheels" in n else SERIES[0] if "pip" in n else SEQUENTIAL[2] for n in names]
    ax.barh(names, mb, color=colours, height=0.6)
    for y, v in enumerate(mb):
        ax.text(v + 3, y, f"{v:.1f} MB" if v >= 1 else f"{v * 1000:.0f} kB", va="center", color=INK["secondary"], fontsize=9)
    ax.set_xlabel("layer size, MB (uncompressed)")
    ax.set_xlim(0, max(mb) * 1.25)
    ax.set_title(f"Image layers: dependencies dominate; the app itself is kilobytes (layers sum to {sum(mb):.0f} MB)")
    save(fig, HERE / "image_layers.svg")


def billed_units() -> None:
    fig, ax = plt.subplots(figsize=(7, 3.0))
    names = [n for n, _, _ in SCENARIOS]
    vals = [units(t, h, 0.25, 0.5)["vcpu_h"] for _, t, h in SCENARIOS]
    ax.barh(names[::-1], vals[::-1], color=[SERIES[1]] * 2 + [SEQUENTIAL[3]] * 2, height=0.55)
    for y, v in enumerate(vals[::-1]):
        ax.text(v + 4, y, f"{v:g} vCPU-h", va="center", color=INK["secondary"], fontsize=9)
    ax.set_xlabel(f"billed vCPU-hours (0.25 vCPU task; a month is {HOURS_PER_MONTH} h)")
    ax.set_xlim(0, max(vals) * 1.3)
    ax.set_title("A demo's cost is set by how long it runs, not by how small it is")
    save(fig, HERE / "billed_units.svg")


if __name__ == "__main__":
    startup()
    layers()
    billed_units()
    print("wrote startup_timeline.svg, image_layers.svg, billed_units.svg")
