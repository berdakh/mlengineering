"""Figures for handbook section H6.7 (error analysis). Deterministic; SYNTHETIC numbers / arithmetic only.

    python handbook/figures/h6_7/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402


def fig_simpson():
    """Same draw as labs/w3d6_error_analysis_transfer/example/slice_traps.py, part 1."""
    rng = np.random.default_rng(7)
    events = np.array([400, 100, 100, 400])
    detected = rng.binomial(events, [0.90, 0.50, 0.94, 0.56])
    recall = detected / events                                   # A steady, A variable, B steady, B variable
    pooled = [detected[:2].sum() / events[:2].sum(), detected[2:].sum() / events[2:].sum()]
    groups = ["steady load", "variable load", "pooled"]
    a, b = [recall[0], recall[1], pooled[0]], [recall[2], recall[3], pooled[1]]
    counts_a, counts_b = [400, 100, 500], [100, 400, 500]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    x = np.arange(3)
    for offset, values, counts, colour, name in ((-0.19, a, counts_a, SERIES[0], "detector A"),
                                                 (0.19, b, counts_b, SERIES[1], "detector B")):
        ax.bar(x + offset, values, width=0.34, color=colour, label=name)
        for xi, value, n in zip(x + offset, values, counts):
            ax.text(xi, value + 0.015, f"{value:.2f}\nn={n}", ha="center", color=INK["secondary"], fontsize=8.5)
    ax.set_xticks(x, groups)
    ax.set_ylim(0, 1.2)
    ax.set_ylabel("recall")
    ax.set_title("SYNTHETIC: B wins in each regime and loses overall, because the mixes differ")
    ax.legend(loc="upper right", ncols=2)
    ax.grid(axis="x", visible=False)
    save(fig, HERE / "simpson_recall.svg")
    print("simpson:", dict(zip(["A steady", "A variable", "B steady", "B variable"], recall.round(3))),
          "pooled A/B", np.round(pooled, 3))


def fig_slice_standard_error():
    k = np.arange(2, 41)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for s, colour in ((0.2, SERIES[0]), (0.3, SERIES[1]), (0.4, SERIES[2])):
        half = 1.96 * s / np.sqrt(k)
        ax.plot(k, half, color=colour, label=f"between-unit sd {s}")
        ax.text(k[-1] + 0.5, half[-1], f"sd {s}", color=INK["secondary"], fontsize=9, va="center")
    ax.axvspan(2, 5, color=INK["grid"], alpha=0.6)
    ax.text(2.2, 0.72, "under 5 units:\nshow the values,\nnot an interval", color=INK["secondary"], fontsize=8.5, va="top")
    ax.set_xlim(2, 44)
    ax.set_ylim(0, 0.8)
    ax.set_xlabel("units (experiments, customers) in the slice")
    ax.set_ylabel("approx. 95 % half-width of the slice mean")
    ax.set_title("A slice of 10 units cannot resolve differences below about 0.2")
    ax.legend(loc="upper right")
    save(fig, HERE / "slice_half_width.svg")
    for s in (0.2, 0.3, 0.4):
        print(f"half-width sd={s}:", {int(n): round(1.96 * s / np.sqrt(n), 3) for n in (5, 10, 25)})


if __name__ == "__main__":
    fig_simpson()
    fig_slice_standard_error()
