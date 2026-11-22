"""Regenerate the figures of lesson w4d6 (REAL SKAB).

    python project/get_skab.py                                           # once
    python lessons/w4d6_project_milestone_1/figures/make_figures.py      # about 10 seconds

1. dev_differences.svg: what the pipeline's report figure looks like, drawn by flowguard.svgplot from
   the reference run's results file (solutions/.../example_report/results.json).
2. test_alarm_strips.svg: the chosen detector (flow-rate |z|) on the 7 frozen test experiments, at the
   operating point stored in that results file: labelled anomaly, alarms, and the calibration window.
matplotlib is needed only for figure 2; the lab and the checks do not import it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REF = ROOT / "solutions" / "lessons" / "w4d6_project_milestone_1"
sys.path[:0] = [str(ROOT), str(REF / "lab" / "src")]

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import extract_events  # noqa: E402
from flowguard.svgplot import interval_plot  # noqa: E402
from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402


def main() -> None:
    res = json.loads((REF / "example_report" / "results.json").read_text())
    pr = res["protocol"]
    interval_plot([{"label": r["name"], "estimate": r["diff"], "lo": r["diff_lo"], "hi": r["diff_hi"]}
                   for r in res["development"] if r["name"] != pr["reference"]],
                  HERE / "dev_differences.svg",
                  title=f"PR-AUC difference to {pr['reference']} (development, paired cluster bootstrap)",
                  xlabel="candidate minus reference; shaded band = ± MPID", band=(-pr["mpid"], pr["mpid"]))
    chosen = next(r for r in res["development"] if r["name"] == res["decision"]["chosen"])
    print(f"chosen {chosen['name']}: threshold {chosen['threshold']:.3f}, min_duration {chosen['min_duration']}, "
          f"merge_gap {chosen['merge_gap']}")

    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    test = tidy[tidy["experiment_id"].isin(pr["test_experiments"])].reset_index(drop=True)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), test, pr["burn_in_rows"])
    apply()
    import matplotlib.pyplot as plt
    ids = pr["test_experiments"]
    fig, axes = plt.subplots(len(ids), 1, figsize=(8.4, 0.62 * len(ids) + 0.9), sharex=True)
    for ax, e in zip(axes, ids):
        g = test[test["experiment_id"] == e].sort_values("t")
        s = scores[g.index.to_numpy()]
        t = g["t"].to_numpy()
        flags = (s >= chosen["threshold"]) & (t >= pr["burn_in_rows"])
        alarms = extract_events(flags, min_duration=chosen["min_duration"], merge_gap=chosen["merge_gap"])
        for a, b in extract_events(g["anomaly"].to_numpy()):
            ax.axvspan(t[a], t[b - 1], ymin=0.55, ymax=0.95, color=SERIES[0], alpha=0.35, lw=0)
        for a, b in alarms:
            ax.axvspan(t[a], t[b - 1], ymin=0.05, ymax=0.45, color=STATUS["serious"], lw=0)
        ax.axvspan(0, pr["burn_in_rows"], color=INK["grid"], alpha=0.8, lw=0)
        ax.set_yticks([])
        ax.set_ylabel(e, rotation=0, ha="right", va="center", fontsize=9, color=INK["primary"])
        ax.grid(False)
        for side in ("left", "top", "right"):
            ax.spines[side].set_visible(False)
    axes[-1].set_xlabel("row (about 1 s per row)")
    axes[0].set_title("Chosen detector on the 7 test runs: labelled anomaly (top band) and alarms (bottom band)")
    fig.text(0.01, 0.005, "grey = calibration rows (not evaluated). REAL SKAB, frozen test set.",
             fontsize=8, color=INK["secondary"])
    save(fig, HERE / "test_alarm_strips.svg")
    print("wrote dev_differences.svg, test_alarm_strips.svg")


if __name__ == "__main__":
    main()
