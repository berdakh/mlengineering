"""Detection delay and event recall against false alarms per hour, on DEV experiments. REAL SKAB data.

    python lessons/w3d4_point_vs_event_evaluation/lab/tradeoff_curve.py
    python lessons/w3d4_point_vs_event_evaluation/lab/tradeoff_curve.py --min-duration 1 --merge-gap 0

Detector: |z| of flow_rate against each experiment's own first 100 rows. One line per threshold.
This is the curve an operating point is chosen from; it uses development experiments only.
This file is complete. It works once flowguard.evaluation is implemented.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"  # frozen split manifest from w3d1
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.splits import dev_experiments, load_splits  # noqa: E402

BURN_IN = 100
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Delay / recall / false-alarm tradeoff on dev.")
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--min-duration", type=int, default=10)
    ap.add_argument("--merge-gap", type=int, default=30)
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)
    is_dev = tidy["experiment_id"].isin(dev_experiments(manifest)).to_numpy()
    dev, dev_scores = tidy[is_dev].reset_index(drop=True), scores[is_dev]
    print(f"dev experiments: {dev['experiment_id'].nunique()}; min_duration={args.min_duration}, "
          f"merge_gap={args.merge_gap}\n")
    print("| threshold (abs z) | events found | false alarms | false alarms / h | median delay s | p90 delay s |")
    print("|---|---|---|---|---|---|")
    show = lambda x: "missed" if math.isinf(x) else f"{x:.0f}"  # noqa: E731
    for threshold in (1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0, 10.0):
        r = evaluate_experiments(dev, dev_scores >= threshold, burn_in=BURN_IN,
                                 min_duration=args.min_duration, merge_gap=args.merge_gap)
        print(f"| {threshold:.1f} | {r['n_detected']}/{r['n_events']} | {r['n_false_alarms']} | "
              f"{r['false_alarms_per_hour']:.1f} | {show(r['median_delay_s'])} | {show(r['p90_delay_s'])} |")
    print(f"\nnormal operation in the evaluated dev rows: {r['normal_hours']:.2f} h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
