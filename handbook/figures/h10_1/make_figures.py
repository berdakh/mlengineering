"""Figures for handbook section H10.1. REAL SKAB data (the 7 frozen test experiments).

    python project/get_skab.py                                  # once
    python handbook/figures/h10_1/make_figures.py [--png DIR]   # about 10 seconds

How large must a skew be before it changes decisions? Every served score is multiplied by (1 + eps),
the kind of error a re-implemented formula introduces (ddof=1 with n=100 rows is eps = +0.5 %), and the
alarm decisions of the shipped detector are compared with the unperturbed ones.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REF = ROOT / "solutions" / "lessons" / "w5d1_inference_pipeline" / "lab"
sys.path[:0] = [str(ROOT), str(REF / "src")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.batch import load_detector  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.inference import serving_frame  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None)
    args = ap.parse_args()
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    test = tidy[tidy["experiment_id"].isin(load_splits(REF / "splits" / "v2.json")["test"])].reset_index(drop=True)
    det = load_detector(REF / "model")
    frame, _ = det.score_batch(serving_frame(test))
    score = frame["score"].to_numpy()
    keep = ~np.isnan(score)
    base_flags = score[keep] >= det.threshold

    def changed(e):
        s = score * (1 + e)
        flips = int(((s[keep] >= det.threshold) != base_flags).sum())
        ev = evaluate_experiments(test, np.nan_to_num(s, nan=-np.inf) >= det.threshold, burn_in=det.n_burn,
                                  min_duration=det.min_duration, merge_gap=det.merge_gap)
        return flips, ev["n_detected"]

    gap = np.min(np.abs(score[keep] - det.threshold) / det.threshold)
    ddof_eps = np.sqrt(99 / 100) - 1            # pandas std (ddof=1) where NumPy (ddof=0) was evaluated
    print(f"scored rows {keep.sum()}; nearest score to the threshold is a relative {gap:.2e} away")
    for e in (-1e-12, -1e-6, -1e-3, ddof_eps, -1e-2, -1e-1, 1e-3, 1e-2, 1e-1):
        f, n = changed(e)
        print(f"  eps {e:+.3e}: raw decisions changed {f}, events detected {n}/7")

    grid = np.logspace(-6, -0.5, 60)
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    for ax, sign, title in ((a1, -1, "scores shrunk by eps"), (a2, 1, "scores inflated by eps")):
        ax.step(grid, [changed(sign * e)[0] for e in grid], where="post", color=SERIES[0], lw=2)
        ax.set_xscale("log")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("relative error eps")
    f_ddof, _ = changed(ddof_eps)
    a1.plot([-ddof_eps], [f_ddof], "o", color=SERIES[1], ms=7, zorder=3)
    a1.annotate(f"ddof=1 instead of 0, n=100:\n{f_ddof} decisions changed", xy=(-ddof_eps, f_ddof),
                xytext=(2e-6, 200), color=INK["secondary"], fontsize=9,
                arrowprops=dict(arrowstyle="-", color=INK["muted"], lw=0.8))
    a2.axvline(gap, color=INK["muted"], lw=1, ls=":")
    a2.text(gap * 1.15, 260, f"nearest score below:\n{gap:.2%} under threshold", color=INK["secondary"], fontsize=9)
    a1.set_ylabel("raw alarm decisions changed\n(of 6,659 scored test rows)")
    fig.suptitle("Real SKAB test runs: a skew changes decisions only once it moves scores across the threshold",
                 x=0.01, y=1.04, ha="left", fontweight="bold", fontsize=11)
    if args.png:
        Path(args.png).mkdir(parents=True, exist_ok=True)
        fig.savefig(Path(args.png) / "tolerance.png", dpi=110)
    save(fig, HERE / "tolerance.svg")
    print("wrote tolerance.svg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
