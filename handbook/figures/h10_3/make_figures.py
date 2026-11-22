"""Figures for handbook section H10.3 (SYNTHETIC data only).

    python handbook/figures/h10_3/make_figures.py      # about 10 s

1. running_mean_drift.svg - absolute error of a running mean accumulated in float32, in float64, and
   with Welford's update in float32, against the number of samples (1e6 samples, mean 1000, SD 1).
   Relevant to edge devices and GPU kernels that accumulate in float32.
2. ring_buffer_cost.svg - time per update of three sliding-window statistics (window mean by ring
   buffer + running sum, window median by sorted list, window median recomputed with sorted()) against
   the window length. Host-dependent; values in figure_data.csv.
"""
from __future__ import annotations

import sys
import time
from bisect import bisect_left, insort
from collections import deque
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

records: list[dict] = []


def fig_drift() -> None:
    rng = np.random.default_rng(3)
    n = 1_000_000
    x64 = 1000.0 + rng.normal(0.0, 1.0, n)
    x32 = x64.astype(np.float32)
    checkpoints = np.unique(np.logspace(1, 6, 26).astype(int))
    naive32 = np.float32(0.0)
    mean_w32 = np.float32(0.0)
    sum64 = 0.0
    errs = {"float32 running sum / n": [], "float32 Welford mean": [], "float64 running sum / n": []}
    ci = 0
    for i in range(n):
        v32 = x32[i]
        naive32 = np.float32(naive32 + v32)
        mean_w32 = np.float32(mean_w32 + np.float32((v32 - mean_w32) / np.float32(i + 1)))
        sum64 += float(v32)
        if ci < len(checkpoints) and i + 1 == checkpoints[ci]:
            exact = float(np.mean(x32[: i + 1].astype(np.float64)))
            for name, value in (("float32 running sum / n", float(naive32) / (i + 1)),
                                ("float32 Welford mean", float(mean_w32)),
                                ("float64 running sum / n", sum64 / (i + 1))):
                e = max(abs(value - exact), 1e-16)
                errs[name].append(e)
                records.append({"figure": "drift", "n": i + 1, "method": name, "abs_error": e})
            ci += 1
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for (name, values), color in zip(errs.items(), (SERIES[1], SERIES[0], SERIES[2])):
        ax.loglog(checkpoints, values, marker="o", markersize=4, color=color, label=name)
        ax.annotate(name, (checkpoints[-1], values[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK["secondary"])
    ax.set_xlabel("samples accumulated")
    ax.set_ylabel("absolute error of the mean")
    ax.set_xlim(8, 4e7)
    ax.set_title("float32: a running sum drifts as the stream grows; an incremental mean stays near resolution (SYNTHETIC)",
                 fontsize=10)
    ax.text(12, 4e-16, "float64 sum of these float32 inputs is exact: error 0, plotted at 1e-16", fontsize=8, color=INK["secondary"])
    ax.legend(loc="upper left")
    save(fig, HERE / "running_mean_drift.svg")


def time_per_update(fn, xs) -> float:
    t0 = time.perf_counter()
    fn(xs)
    return (time.perf_counter() - t0) / len(xs) * 1e6


def window_mean(w):
    def run(xs):
        ring, s = deque(), 0.0
        for x in xs:
            ring.append(x)
            s += x
            if len(ring) > w:
                s -= ring.popleft()
    return run


def window_median_sorted(w):
    def run(xs):
        ring, srt = deque(), []
        for x in xs:
            ring.append(x)
            insort(srt, x)
            if len(ring) > w:
                del srt[bisect_left(srt, ring.popleft())]
            _ = srt[len(srt) // 2]
    return run


def window_median_resort(w):
    def run(xs):
        ring = deque(maxlen=w)
        for x in xs:
            ring.append(x)
            _ = sorted(ring)[len(ring) // 2]
    return run


def fig_ring() -> None:
    rng = np.random.default_rng(4)
    xs = rng.normal(size=20_000).tolist()
    windows = [10, 30, 100, 300, 1000, 3000]
    series = {"mean: ring buffer + running sum": window_mean,
              "median: ring buffer + sorted list (bisect)": window_median_sorted,
              "median: sorted(window) on every update": window_median_resort}
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for (name, factory), color in zip(series.items(), (SERIES[0], SERIES[2], SERIES[1])):
        ys = []
        for w in windows:
            data = xs if "sorted(window)" not in name or w <= 300 else xs[:3000]
            us = min(time_per_update(factory(w), data) for _ in range(2))
            ys.append(us)
            records.append({"figure": "ring", "window": w, "method": name, "us_per_update": us})
        ax.loglog(windows, ys, marker="o", color=color, label=name)
    ax.set_xlabel("window length (samples)")
    ax.set_ylabel("µs per update (log)")
    ax.set_title("Sliding-window cost per sample: O(1), O(w) memmove, O(w log w) (SYNTHETIC; host-dependent)")
    ax.legend(loc="upper left", fontsize=8)
    save(fig, HERE / "ring_buffer_cost.svg")


def main() -> None:
    fig_drift()
    fig_ring()
    pd.DataFrame(records).to_csv(HERE / "figure_data.csv", index=False)
    df = pd.DataFrame(records)
    print(df[df.figure == "drift"].groupby("method").abs_error.last())
    print(df[df.figure == "ring"].pivot(index="window", columns="method", values="us_per_update").round(2))


if __name__ == "__main__":
    main()
