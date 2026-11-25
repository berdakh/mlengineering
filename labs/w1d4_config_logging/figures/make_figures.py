"""Figures for lesson w1d4, from the reference solution on the SYNTHETIC pump data.

    python labs/w1d4_config_logging/figures/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "labs" / "w1d4_config_logging" / "lab" / "src"))
from pumpwatch.features import build_feature_table  # noqa: E402
from pumpwatch.io import load_windows  # noqa: E402
from pumpwatch.model import train_and_evaluate  # noqa: E402
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

OUT = Path(__file__).resolve().parent


def main() -> None:
    apply()
    import matplotlib.pyplot as plt
    table = build_feature_table(load_windows(ROOT / "data" / "synthetic" / "pump_vibration.csv"), fs=256.0)
    seeds = list(range(10))
    runs = [train_and_evaluate(table, seed=s) for s in seeds]
    f1 = np.array([r["f1"] for r in runs])
    mean, sd = f1.mean(), f1.std(ddof=1)

    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.axhspan(mean - sd, mean + sd, color=SERIES[0], alpha=0.10, lw=0)
    ax.axhline(mean, color=INK["muted"], lw=1.0, ls="--")
    ax.scatter(seeds, f1, s=46, color=SERIES[0], zorder=3)
    for s, r in zip(seeds, runs):
        ax.annotate(" ".join(u[1:] for u in r["test_units"]), (s, r["f1"]), textcoords="offset points",
                    xytext=(0, 8), ha="center", fontsize=7, color=INK["secondary"])
    ax.text(9.95, mean, f"mean {mean:.3f}\n± s.d. {sd:.3f}", va="center", fontsize=8, color=INK["secondary"])
    ax.set_xticks(seeds)
    ax.set_xlim(-0.6, 11.4)
    ax.set_ylim(f1.min() - 0.03, f1.max() + 0.04)
    ax.set_xlabel("split seed (numbers above each point: held-out units)")
    ax.set_ylabel("test F1")
    ax.set_title(f"SYNTHETIC: identical code and data, ten split seeds, F1 from {f1.min():.3f} to {f1.max():.3f}")
    ax.grid(axis="x", visible=False)
    save(fig, OUT / "seed_spread.svg")
    print("seed  f1     held-out")
    for s, r in zip(seeds, runs):
        print(f"{s:>4}  {r['f1']:.3f}  {' '.join(r['test_units'])}")
    print(f"min {f1.min():.3f} max {f1.max():.3f} mean {mean:.3f} sd {sd:.3f}")


if __name__ == "__main__":
    main()
