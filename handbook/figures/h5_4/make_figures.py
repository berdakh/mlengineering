"""Figures for handbook H5.4 (complexity versus evidence). All SYNTHETIC; deterministic.

    python handbook/figures/h5_4/make_figures.py      # about 1 minute

1. power_for_mpid.svg: probability that a 95 % interval for a paired difference lands wholly above
   the MPID, as a function of the number of independent clusters, for several true differences.
   Model: per-cluster differences ~ Normal(delta, sd_between = 0.12); interval = mean ± t * se.
2. forecast_front.svg: the w4d5 worked example's candidates (MAPE against pickled size), from
   lessons/w4d5_model_choice/example/forecast_choice.py, rerun here.
"""
from __future__ import annotations

import io
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "lessons" / "w4d5_model_choice" / "example")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

MPID, SD_BETWEEN = 0.05, 0.12


def power_table() -> pd.DataFrame:
    rng = np.random.default_rng(3)
    rows = []
    for delta in (0.05, 0.07, 0.10, 0.15):
        for g in (5, 7, 10, 15, 20, 30, 50, 80):
            d = rng.normal(delta, SD_BETWEEN, size=(4000, g))
            mean, se = d.mean(axis=1), d.std(axis=1, ddof=1) / np.sqrt(g)
            lo = mean - stats.t.ppf(0.975, g - 1) * se
            rows.append({"true_delta": delta, "clusters": g, "p_wholly_above_mpid": float((lo > MPID).mean()),
                         "p_excludes_zero": float((lo > 0).mean())})
    return pd.DataFrame(rows)


def fig_power(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 3.8))
    for color, (delta, g) in zip(SERIES, df.groupby("true_delta")):
        ax.plot(g["clusters"], g["p_wholly_above_mpid"], "o-", color=color, ms=5)
        ax.annotate(f"true Δ = +{delta:.2f}", (g["clusters"].iloc[-1], g["p_wholly_above_mpid"].iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", va="center", fontsize=9, color=INK["secondary"])
    ax.axvline(23, color=INK["axis"], lw=1, ls="--")
    ax.text(24, 0.72, "flowguard dev:\n23 clusters", fontsize=8, color=INK["secondary"], va="center")
    ax.set_xscale("log")
    ax.set_xticks([5, 7, 10, 15, 20, 30, 50, 80])
    ax.set_xticklabels(["5", "7", "10", "15", "20", "30", "50", "80"])
    ax.set_xlim(4.5, 140)
    ax.set_ylim(-0.02, 1.02)
    ax.set_xlabel("independent clusters in the comparison")
    ax.set_ylabel("P(interval wholly above +MPID)")
    ax.set_title("Showing a gain is practically important needs many clusters (SYNTHETIC, MPID 0.05)")
    save(fig, HERE / "power_for_mpid.svg")


def fig_front() -> pd.DataFrame:
    import forecast_choice
    buf = io.StringIO()
    with redirect_stdout(buf):
        forecast_choice.main()
    lines = [ln for ln in buf.getvalue().splitlines() if re.match(r"^\s*(seasonal-naive|ridge|boosted trees)\s", ln)]
    rows = []
    for ln in lines:
        name = "boosted trees" if ln.strip().startswith("boosted") else ln.split()[0]
        nums = ln.replace(name, "").split()
        rows.append({"name": name, "mape": float(nums[1]), "size_bytes": max(float(nums[7]), 1.0)})
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(6.0, 3.4))
    for color, (_, r) in zip(SERIES, df.iterrows()):
        ax.plot(r["size_bytes"], r["mape"], "o", color=color, ms=9, mec=INK["surface"], mew=1.5)
        ax.annotate(r["name"], (r["size_bytes"], r["mape"]), xytext=(9, -3), textcoords="offset points",
                    fontsize=9, color=INK["secondary"])
    ax.set_xscale("log")
    ax.set_xlim(1, 3e7)
    ax.set_xlabel("pickled model size, bytes (log)")
    ax.set_ylabel("test MAPE, % (lower is better)")
    ax.set_title("Boosted trees are dominated by ridge: worse error, 1,500x the size (SYNTHETIC)")
    save(fig, HERE / "forecast_front.svg")
    return df


def main() -> None:
    df = power_table()
    df.to_csv(HERE / "power_for_mpid.csv", index=False)
    print(df.pivot(index="clusters", columns="true_delta", values="p_wholly_above_mpid").round(2).to_string())
    fig_power(df)
    front = fig_front()
    front.to_csv(HERE / "forecast_front.csv", index=False)
    print(front.to_string(index=False))


if __name__ == "__main__":
    main()
