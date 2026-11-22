"""Regenerate every figure of lesson w4d5.

    python project/get_skab.py                                   # once
    python lessons/w4d5_model_choice/figures/make_figures.py     # about 2.5 minutes

Figures 1-3 use REAL SKAB results: this script runs the reference decision_table.py (solutions tree)
and plots its CSV output, which it also copies here (decision_table.csv, test_look.csv).
Latency and fit times depend on the host and its load; the authoring run's values are what the
lesson quotes. Figure 4 is a SYNTHETIC schematic of the interval-versus-MPID rule.
matplotlib is needed only here; the lab and the checks do not import it.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE_LAB = ROOT / "solutions" / "lessons" / "w4d5_model_choice" / "lab"
sys.path[:0] = [str(ROOT), str(REFERENCE_LAB)]

from tools.figstyle import DIVERGING, INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

MPID = 0.05
COLOR = {"flow-rate |z|": SERIES[0], "Mahalanobis": SERIES[1], "isolation forest": SERIES[2],
         "logistic (supervised)": SERIES[3]}


def run_reference() -> pd.DataFrame:
    import decision_table
    out = HERE / "_run"
    if decision_table.main(["--out", str(out)]) != 0:
        raise SystemExit("reference run failed (is data/raw/skab present? run project/get_skab.py)")
    for name in ("decision_table.csv", "test_look.csv"):
        shutil.copy(out / name, HERE / name)
    shutil.rmtree(out)
    return pd.read_csv(HERE / "decision_table.csv")


def fig_intervals(t: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    ax.axvspan(-MPID, MPID, color=INK["grid"], alpha=0.6, lw=0)
    ax.axvline(0, color=INK["axis"], lw=1)
    rows = t[t["name"] != t["name"].iloc[0]].reset_index(drop=True)
    for i, r in rows.iterrows():
        y = len(rows) - 1 - i
        ax.plot([r["diff_lo"], r["diff_hi"]], [y, y], color=COLOR[r["name"]], lw=2.5, solid_capstyle="round")
        ax.plot(r["diff"], y, "o", color=COLOR[r["name"]], ms=7, mec=INK["surface"], mew=1.5)
        ax.text(r["diff_hi"] + 0.012, y, f"{r['diff']:+.3f} [{r['diff_lo']:+.3f}, {r['diff_hi']:+.3f}]  {r['vs_reference']}",
                va="center", fontsize=9, color=INK["secondary"])
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows["name"][::-1])
    ax.set_xlim(-0.33, 0.42)
    ax.set_xlabel("PR-AUC difference to flow-rate |z| (development, paired cluster bootstrap 95 %)")
    ax.set_ylim(-0.9, len(rows) - 0.5)
    ax.text(0, -0.75, "±MPID 0.05", ha="center", va="bottom", fontsize=8, color=INK["secondary"])
    ax.set_title("Only the forest is shown different, and it is worse; the logistic gain is not shown to matter")
    ax.grid(axis="y", visible=False)
    save(fig, HERE / "dev_intervals.svg")


def fig_pareto(t: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    front = t[t["pareto"]].sort_values("p95_ms")
    ax.plot(front["p95_ms"], front["primary"], color=INK["axis"], lw=1.2, ls="--", zorder=1)
    for _, r in t.iterrows():
        ax.errorbar(r["p95_ms"], r["primary"], yerr=[[r["primary"] - r["primary_lo"]], [r["primary_hi"] - r["primary"]]],
                    fmt="o", color=COLOR[r["name"]], ms=8, mec=INK["surface"], mew=1.5, elinewidth=1.5, capsize=0, zorder=2)
        dy = -12 if r["name"] == "Mahalanobis" else (6 if r["name"] == "flow-rate |z|" else -3)
        ax.annotate(f"{r['name']}{'  (front)' if r['pareto'] else ''}", (r["p95_ms"], r["primary"]),
                    xytext=(8, dy), textcoords="offset points", fontsize=9, color=INK["secondary"])
    ax.set_xscale("log")
    ax.set_xlim(0.1, 200)
    ax.set_xlabel("p95 latency per sample, ms (log scale; authoring host)")
    ax.set_ylabel("PR-AUC, development (95 % CI)")
    ax.set_title("Two candidates are on the Pareto front; the front does not choose between them")
    save(fig, HERE / "pareto.svg")


def fig_costs(t: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(9.6, 2.8), sharey=True)
    specs = [("p95_ms", "p95 latency, ms"), ("size_bytes", "pickled step, bytes"), ("fit_s", "fit + calibrate, s")]
    y = np.arange(len(t))[::-1]
    for ax, (col, label) in zip(axes, specs):
        ax.barh(y, t[col], color=[COLOR[n] for n in t["name"]], height=0.6)
        ax.set_xscale("log")
        ax.set_xlabel(label)
        for yi, v in zip(y, t[col]):
            ax.text(v * 1.15, yi, f"{v:,.3g}", va="center", fontsize=8, color=INK["secondary"])
        ax.set_xlim(t[col].min() / 3, t[col].max() * 12)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(t["name"])
    fig.suptitle("Run-time costs differ by orders of magnitude; most accuracy differences do not clear the MPID",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, HERE / "costs.svg")


def fig_schematic() -> None:
    cases = [("better", 0.07, 0.13), ("equivalent", -0.03, 0.035), ("inconclusive: excludes 0", 0.01, 0.09),
             ("inconclusive: wide", -0.09, 0.08), ("worse", -0.15, -0.07)]
    tone = {"better": STATUS["good"], "equivalent": SERIES[0], "worse": STATUS["critical"]}
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    ax.axvspan(-MPID, MPID, color=INK["grid"], alpha=0.6, lw=0)
    ax.axvline(0, color=INK["axis"], lw=1)
    for i, (label, lo, hi) in enumerate(cases):
        y = len(cases) - 1 - i
        c = tone.get(label, INK["muted"])
        ax.plot([lo, hi], [y, y], color=c, lw=3, solid_capstyle="round")
        ax.text(0.16, y, label, va="center", fontsize=9, color=INK["primary"])
    ax.set_yticks([])
    ax.set_xlim(-0.2, 0.32)
    ax.set_xticks([-0.1, -MPID, 0, MPID, 0.1])
    ax.set_xticklabels(["-0.10", "-MPID", "0", "+MPID", "+0.10"])
    ax.set_xlabel("interval for candidate - reference (higher is better)")
    ax.set_title("Read the whole interval against ±MPID (SYNTHETIC schematic)")
    ax.grid(False)
    save(fig, HERE / "interval_rule.svg")


def main() -> None:
    t = run_reference()
    print(t[["name", "primary", "diff", "diff_lo", "diff_hi", "vs_reference", "p95_ms", "size_bytes", "fit_s", "pareto"]]
          .to_string(index=False))
    fig_intervals(t)
    fig_pareto(t)
    fig_costs(t)
    fig_schematic()
    print("wrote", ", ".join(p.name for p in sorted(HERE.glob("*.svg"))))


if __name__ == "__main__":
    main()
