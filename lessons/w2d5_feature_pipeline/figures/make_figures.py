"""Figures for w2d5 and handbook H7.1 (SYNTHETIC data: noise plus a step of known height).

    python lessons/w2d5_feature_pipeline/figures/make_figures.py

Reuses the simulation of example/lookahead_demo.py with the same seed and loop order, so the medians
printed here equal part 1 of that script's output.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "example"))

import lookahead_demo as demo  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

CAUSAL, CENTRED = SERIES[0], SERIES[1]   # fixed for every figure of this lesson
THETA = 0.25 * demo.DELTA


def step_response(w: int = 30) -> None:
    x = pd.Series(demo.simulate(np.random.default_rng(1)))
    causal = x.rolling(w, min_periods=w).mean()
    centred = x.rolling(w, min_periods=w, center=True).mean()
    d_causal, d_centred = demo.first_crossing(causal, THETA), demo.first_crossing(centred, THETA)
    lo, hi = demo.ONSET - 70, demo.ONSET + 70
    t = np.arange(demo.N) - demo.ONSET
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(t[lo:hi], x[lo:hi], color=INK["axis"], linewidth=1, label="signal (noise + step)")
    ax.plot(t[lo:hi], causal[lo:hi], color=CAUSAL, label=f"causal mean, last {w} samples")
    ax.plot(t[lo:hi], centred[lo:hi], color=CENTRED, label=f"centred mean, {w} samples around t")
    ax.axhline(THETA, color=INK["secondary"], linestyle="--", linewidth=1.2)
    ax.text(hi - demo.ONSET - 1, THETA + 0.08, "alert threshold", ha="right", color=INK["secondary"], fontsize=9)
    ax.axvline(0, color=INK["primary"], linewidth=1)
    ax.text(1.5, x[lo:hi].max(), "fault onset", va="top", color=INK["primary"], fontsize=9)
    for d, colour in ((d_causal, CAUSAL), (d_centred, CENTRED)):
        ax.scatter([d], [THETA], s=60, color=colour, edgecolor=INK["surface"], linewidth=1.5, zorder=4)
    ax.annotate(f"alert {d_causal:+.0f}", (d_causal, THETA), (d_causal + 6, THETA - 0.55), color=INK["primary"],
                arrowprops={"arrowstyle": "-", "color": INK["muted"]})
    ax.annotate(f"alert {d_centred:+.0f}\n(before the fault)", (d_centred, THETA), (d_centred - 36, THETA + 0.75),
                color=INK["primary"], arrowprops={"arrowstyle": "-", "color": INK["muted"]})
    ax.set_xlabel("samples relative to fault onset")
    ax.set_ylabel("value")
    ax.set_title("A centred window raises the alert before the fault exists (SYNTHETIC)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=3)
    save(fig, HERE / "step_response.svg")
    print(f"single series (seed 1), w={w}: causal alert at {d_causal:+.0f}, centred alert at {d_centred:+.0f}")


def delay_vs_window() -> None:
    rng = np.random.default_rng(0)                       # same seed and order as lookahead_demo.main
    rows = []
    for w in demo.WINDOWS:
        causal, centred = [], []
        for _ in range(demo.N_REPEATS):
            x = pd.Series(demo.simulate(rng))
            causal.append(demo.first_crossing(x.rolling(w, min_periods=w).mean(), THETA))
            centred.append(demo.first_crossing(x.rolling(w, min_periods=w, center=True).mean(), THETA))
        rows.append((w, w * THETA / demo.DELTA, np.nanmedian(causal), np.nanmedian(centred)))
        print(f"w={w:>3} predicted {rows[-1][1]:>5.1f}  causal {rows[-1][2]:>5.1f}  centred {rows[-1][3]:>6.1f}")
    ws = np.array([r[0] for r in rows])
    grid = np.linspace(5, 65, 50)
    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    ax.axhline(0, color=INK["primary"], linewidth=1)
    ax.fill_between(grid, -20, 0, color=CENTRED, alpha=0.08)
    ax.text(64, -1.8, "negative delay: the alert precedes the fault", color=INK["secondary"], fontsize=9, ha="right")
    ax.plot(grid, grid * THETA / demo.DELTA, color=INK["muted"], linestyle="--", linewidth=1.2)
    ax.text(64, 64 * THETA / demo.DELTA + 1.0, "w·θ/Δ", ha="right", color=INK["secondary"], fontsize=9)
    ax.plot(ws, [r[2] for r in rows], marker="o", color=CAUSAL, label="causal window")
    ax.plot(ws, [r[3] for r in rows], marker="o", color=CENTRED, label="centred window")
    for r in rows:
        ax.text(r[0], r[2] + 1.4, f"{r[2]:.0f}", ha="center", color=INK["primary"], fontsize=9)
        ax.text(r[0], r[3] - 3.0, f"{r[3]:.0f}", ha="center", color=INK["primary"], fontsize=9)
    ax.set_xticks(ws)
    ax.set_ylim(-20, 20)
    ax.set_xlabel("window length w (samples)")
    ax.set_ylabel("median detection delay (samples)")
    ax.set_title("Longer windows detect later; centring hides the cost (SYNTHETIC)")
    ax.legend(loc="upper left")
    save(fig, HERE / "delay_vs_window.svg")


if __name__ == "__main__":
    step_response()
    delay_vs_window()
