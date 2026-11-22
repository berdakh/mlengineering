"""Figure for handbook H7.3: the matching rule decides how good a clock looks. REAL SKAB data.

    python project/get_skab.py            # once
    python handbook/figures/h7_3/make_figures.py

Nine test experiments of the project split (manifest v2, seed 0), thresholds from the 25 development
experiments (best point F1). Two detectors: elapsed time (no sensors) and |z| of flow rate with a
100-row burn-in reference (alarms post-processed with min_duration 10, merge_gap 30). Three rules.
Uses the reference flowguard package of lesson w3d4.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "solutions" / "lessons" / "w3d4_point_vs_event_evaluation" / "lab" / "src"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.benchmark import evaluate_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import extract_events, match_events  # noqa: E402
from flowguard.splits import SKAB_OVERLAP_GROUPS, make_splits  # noqa: E402

BURN_IN = 100


def found(test, flags, rule: str, min_duration: int, merge_gap: int) -> tuple[int, int]:
    """(events found, false alarms) pooled over test experiments under one matching rule."""
    n_found = n_false = 0
    frame = test.assign(_flag=flags)
    for _, g in frame.groupby("experiment_id", sort=False):
        true = extract_events(g["anomaly"].to_numpy())
        alarms = extract_events(g["_flag"].to_numpy(), min_duration=min_duration, merge_gap=merge_gap)
        if rule == "any overlap":
            n_found += sum(any(a < te and b > ts for a, b in alarms) for ts, te in true)
            n_false += sum(not any(a < te and b > ts for ts, te in true) for a, b in alarms)
        else:
            m = match_events(true, alarms, early_tolerance=int(rule.split()[-1]))
            n_found += sum(d is not None for d in m["first_detection"])
            n_false += m["pred_label"].count("false_alarm")
    return n_found, n_false


def main() -> None:
    apply()
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    manifest = make_splits(tidy, seed=0, keep_together=SKAB_OVERLAP_GROUPS)
    in_test = (tidy["experiment_id"].isin(manifest["test"]) & (tidy["t"] >= BURN_IN)).to_numpy()
    test = tidy[in_test].reset_index(drop=True)
    detectors = {
        "elapsed time (no sensors)": (tidy["t"].to_numpy(dtype=float), 1, 0),
        "flow-rate |z|, burn-in": (burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN), 10, 30),
    }
    rules = ["any overlap", "start inside event, early tolerance 0", "start inside event, early tolerance 5"]
    short = ["any overlap", "alarm starts in event\n(tolerance 0 rows)", "alarm starts in event\n(tolerance 5 rows)"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.6), sharey=True)
    for ax, (name, (scores, md, mg)), colour in zip(axes, detectors.items(), (SERIES[1], SERIES[0])):
        threshold = evaluate_scores(tidy, scores, manifest, burn_in=BURN_IN)["threshold"]
        flags = (scores[in_test] >= threshold).astype(int)
        counts = [found(test, flags, rule, md, mg) for rule in rules]
        for rule, (n, fa) in zip(rules, counts):
            print(f"{name}: {rule}: {n}/9 events found, {fa} false alarms")
        ax.bar(range(3), [c[0] for c in counts], color=colour, width=0.6)
        for x, (n, fa) in enumerate(counts):
            ax.text(x, n + 0.15, f"{n}/9", ha="center", fontsize=10)
            ax.text(x, 0.25, f"{fa} false\nalarms", ha="center", fontsize=8, color=INK["surface"])
        ax.set_xticks(range(3), short, fontsize=8)
        ax.set_title(name)
        ax.set_ylim(0, 10.5)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("test events counted as detected (of 9)")
    fig.suptitle("Real SKAB, 9 test experiments: under 'any overlap' a clock detects almost everything",
                 x=0.01, y=1.04, ha="left", fontsize=10, color=INK["secondary"])
    save(fig, HERE / "matching_rule_matters.svg")


if __name__ == "__main__":
    main()
