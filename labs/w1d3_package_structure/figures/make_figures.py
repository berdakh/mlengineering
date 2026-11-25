"""Figures for lesson w1d3, from the SYNTHETIC pump data (data/synthetic/pump_vibration.csv).

    python labs/w1d3_package_structure/figures/make_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "labs" / "w1d3_package_structure" / "lab" / "src"))
from pumpwatch.features import HIGH_BAND_HZ, LOW_BAND_HZ, build_feature_table, fill_gaps  # noqa: E402
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

OUT = Path(__file__).resolve().parent
FS = 256.0
HEALTHY, FAULTY = SERIES[0], SERIES[1]


def psd(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    p = np.abs(np.fft.rfft(x - x.mean())) ** 2 / (FS * n)
    p[1:-1] *= 2
    return np.fft.rfftfreq(n, 1 / FS), p


def main() -> None:
    apply()
    import matplotlib.pyplot as plt
    df = pd.read_csv(ROOT / "data" / "synthetic" / "pump_vibration.csv")
    feats = build_feature_table(df, fs=FS)

    # --- one unit, one window before the fault and the last window after it -----------
    unit = "P09"
    u = feats[feats.unit_id == unit]
    w_ok, w_bad = int(u[u.label == 0].window_id.iloc[0]), int(u[u.label == 1].window_id.iloc[-1])
    fig, axes = plt.subplots(2, 2, figsize=(9, 5), gridspec_kw={"width_ratios": [1.25, 1]})
    for row, (w, colour, name) in enumerate([(w_ok, HEALTHY, "healthy"), (w_bad, FAULTY, "faulty")]):
        x = fill_gaps(df[(df.unit_id == unit) & (df.window_id == w)].sort_values("sample").vibration.to_numpy())
        axes[row, 0].plot(np.arange(len(x)) / FS, x, color=colour, lw=1.2)
        axes[row, 0].set_ylabel("vibration (a.u.)")
        axes[row, 0].set_title(f"{unit}, window {w}: {name}", fontweight="normal", fontsize=9, color=INK["secondary"])
        f, p = psd(x)
        for lo, hi in (LOW_BAND_HZ, HIGH_BAND_HZ):
            axes[row, 1].axvspan(lo, hi, color=INK["muted"], alpha=0.15, lw=0)
        axes[row, 1].plot(f, p, color=colour, lw=1.4)
        axes[row, 1].set_ylabel("power density")
        top = axes[row, 1].get_ylim()[1] * 1.18
        axes[row, 1].set_ylim(top=top)
        axes[row, 1].text(25, top, "bp_low", ha="center", va="top", fontsize=8, color=INK["secondary"])
        axes[row, 1].text(90, top, "bp_high", ha="center", va="top", fontsize=8, color=INK["secondary"])
    axes[1, 0].set_xlabel("time (s)")
    axes[1, 1].set_xlabel("frequency (Hz)")
    fig.suptitle("SYNTHETIC pump: the fault adds a 90 Hz component that the bp_high feature isolates",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, OUT / "pump_signal_spectrum.svg")

    # --- between-unit differences versus the fault effect -------------------------------
    units = sorted(feats.unit_id.unique())
    rng = np.random.default_rng(0)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=False)
    for ax, col, title in [(axes[0], "rms", "rms: units differ more than healthy vs faulty"),
                           (axes[1], "ratio", "ratio = bp_high / bp_low: gain cancels")]:
        for i, uid in enumerate(units):
            for label, colour in ((0, HEALTHY), (1, FAULTY)):
                v = feats[(feats.unit_id == uid) & (feats.label == label)][col]
                ax.scatter(i + rng.uniform(-0.18, 0.18, len(v)), v, s=11, color=colour, alpha=0.75, lw=0,
                           label={0: "healthy window", 1: "faulty window"}[label] if i == 2 else None)
        ax.set_xticks(range(len(units)), units, fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_ylabel(col)
        ax.grid(axis="x", visible=False)
    axes[1].set_yscale("log")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncols=2, bbox_to_anchor=(0.5, -0.06))
    fig.suptitle("SYNTHETIC pump: why the split must be by unit, and why a ratio feature travels across units",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, OUT / "unit_vs_fault.svg")
    g = feats.groupby("unit_id").rms.mean()
    print(f"window {w_ok} (healthy) and {w_bad} (faulty) of {unit}")
    print(f"mean rms per unit: min {g.min():.2f} max {g.max():.2f}; "
          f"healthy mean {feats[feats.label == 0].rms.mean():.2f}, faulty mean {feats[feats.label == 1].rms.mean():.2f}")


if __name__ == "__main__":
    main()
