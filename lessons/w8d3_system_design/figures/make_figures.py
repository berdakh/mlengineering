"""Regenerate the data figures of lesson w8d3 and handbook H16.3.

    python lessons/w8d3_system_design/figures/make_figures.py

All three figures are planning arithmetic, not measurements: they plot the formulas of the estimation
worksheet under assumptions stated here and in the worked example. Every plotted number is written to
figure_data.csv. Optional third argument: a directory for PNG copies (for render checks).
"""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

ROWS: list[dict] = []
PNG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def _save(fig, name: str) -> None:
    if PNG_DIR:
        PNG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(PNG_DIR / f"{name}.png", dpi=110)
    save(fig, HERE / f"{name}.svg")


def labels_vs_window() -> None:
    """Labels usable today vs the evaluation window, for several label delays (1,000 predictions/day, 5 % labelled)."""
    per_day, rate = 1_000, 0.05
    windows = list(range(0, 91))
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for colour, delay in zip(SERIES, (1, 7, 14, 28)):
        ys = [per_day * rate * max(0, w - delay) for w in windows]
        ax.plot(windows, ys, color=colour, label=f"label delay {delay} d")
        ax.annotate(f"{delay} d", (windows[-1], ys[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", color=INK["secondary"], fontsize=9)
        for w, y in zip(windows[::15], ys[::15]):
            ROWS.append({"figure": "labels_vs_window", "series": f"delay_{delay}", "x": w, "y": y})
    ax.axhline(385, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(45, 300, "385 labels: +/-5 pt on a proportion near 0.5", color=INK["secondary"], fontsize=9, va="top")
    ax.set_xlabel("evaluation window (days of predictions)")
    ax.set_ylabel("labelled examples available")
    ax.set_title("A long label delay costs evaluation data you cannot buy back")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 100)
    _save(fig, "labels_vs_window")


def half_width_vs_n() -> None:
    """Normal-approximation 95 % half-width of a proportion vs number of labels, for three base rates."""
    ns = [int(round(10 ** (k / 20))) for k in range(40, 101)]  # 100 .. 100,000
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for colour, p in zip(SERIES, (0.5, 0.1, 0.01)):
        hw = [1.96 * math.sqrt(p * (1 - p) / n) * 100 for n in ns]
        ax.plot(ns, hw, color=colour, label=f"p = {p}")
        ax.annotate(f"p = {p}", (ns[-1], hw[-1]), xytext=(4, 0), textcoords="offset points", va="center",
                    color=INK["secondary"], fontsize=9)
        for n, h in zip(ns[::10], hw[::10]):
            ROWS.append({"figure": "half_width_vs_n", "series": f"p_{p}", "x": n, "y": round(h, 4)})
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("labelled examples (log scale)")
    ax.set_ylabel("95 % half-width (percentage points)")
    ax.set_title("Four times the labels for half the interval width")
    ax.legend(loc="lower left")
    ax.set_xlim(100, 300_000)
    _save(fig, "half_width_vs_n")


def latency_budget() -> None:
    """Where the 400 ms budget of the worked example goes (assumed p99 per component)."""
    parts = [("image fetch from object store", 120), ("image embedding (GPU service)", 90),
             ("api gateway + auth", 30), ("feature lookup", 25), ("text features", 15), ("model", 12)]
    fig, ax = plt.subplots(figsize=(7, 3.2))
    names = [n for n, _ in parts][::-1]
    values = [v for _, v in parts][::-1]
    colours = [SERIES[1] if n == "model" else SERIES[0] for n in names]
    ax.barh(names, values, color=colours, height=0.6)
    for y, v in enumerate(values):
        ax.text(v + 2, y, f"{v} ms", va="center", fontsize=9, color=INK["secondary"])
    for n, v in parts:
        ROWS.append({"figure": "latency_budget", "series": n, "x": "", "y": v})
    total = sum(values)
    ax.set_xlim(0, 160)
    ax.set_xlabel("assumed p99 per component (ms)")
    ax.set_title(f"Request path {total} ms of a 400 ms budget; the model is 12 ms of it")
    ax.grid(axis="y", visible=False)
    _save(fig, "latency_budget")


def main() -> None:
    labels_vs_window()
    half_width_vs_n()
    latency_budget()
    with open(HERE / "figure_data.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
        writer.writeheader()
        writer.writerows(ROWS)
    print(f"wrote 3 figures and {len(ROWS)} rows to {HERE}")


if __name__ == "__main__":
    main()
