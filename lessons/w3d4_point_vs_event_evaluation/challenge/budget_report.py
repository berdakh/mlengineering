"""Alert-budget report on the REAL SKAB data. Complete: it works once operating_point.py is implemented.

    python project/get_skab.py                                                   # once
    python lessons/w3d4_point_vs_event_evaluation/challenge/budget_report.py

Detector: |z| of flow_rate against each experiment's own first 100 rows (the w2d6 bar to beat).
Budget: at most one false alarm per 8 hours of normal operation.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

import _paths  # noqa: F401
from flowguard.baselines import SingleSensorZScorer, burn_in_scores
from flowguard.data import load_raw
from flowguard.evaluation import evaluate_experiments
from flowguard.splits import dev_experiments, load_splits, validate_splits
from operating_point import choose_operating_point, rate_upper_bound

BURN_IN = 100
BUDGET = 1 / 8
HERE = Path(__file__).resolve().parent
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)


def line(name: str, r: dict) -> str:
    delay = lambda x: "missed" if math.isinf(x) else f"{x:.0f} s"  # noqa: E731
    return (f"{name:<22} events {r['n_detected']}/{r['n_events']}, alarms {r['n_alarms']} "
            f"(false {r['n_false_alarms']}, redundant {r['n_redundant']}), normal {r['normal_hours']:.2f} h, "
            f"false alarms/h {r['false_alarms_per_hour']:.2f} "
            f"(95 % upper bound {rate_upper_bound(r['n_false_alarms'], r['normal_hours']):.2f}), "
            f"median delay {delay(r['median_delay_s'])}, p90 {delay(r['p90_delay_s'])}; "
            f"delays of the detected only: {sorted(round(d) for d in r['delays_s'] if math.isfinite(d))}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Operating point under an alert budget.")
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    validate_splits(manifest, tidy)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)
    part = {name: tidy["experiment_id"].isin(ids).to_numpy() for name, ids in
            (("dev", dev_experiments(manifest)), ("test", manifest["test"]), ("reference", manifest["reference_normal"]))}
    dev, dev_scores = tidy[part["dev"]].reset_index(drop=True), scores[part["dev"]]
    usable = dev_scores[dev["t"].to_numpy() >= BURN_IN]
    thresholds = np.unique(np.quantile(usable, np.linspace(0.50, 0.999, 40)))
    chosen = choose_operating_point(dev, dev_scores, BUDGET, thresholds, min_durations=(1, 3, 5, 10, 20, 30, 60),
                                    merge_gaps=(0, 5, 10, 30, 60), burn_in=BURN_IN)
    print(f"budget: {BUDGET:.3f} false alarms per hour (1 per 8 h); grid: {len(thresholds)} thresholds x 7 x 5")
    print(f"chosen on dev: threshold {chosen['threshold']:.2f}, min_duration {chosen['min_duration']}, "
          f"merge_gap {chosen['merge_gap']}, feasible on dev: {chosen['feasible']}\n")
    print(line("dev (selection data)", chosen["dev"]))
    for name in ("test", "reference"):
        frame = tidy[part[name]].reset_index(drop=True)
        result = evaluate_experiments(frame, scores[part[name]] >= chosen["threshold"], burn_in=BURN_IN,
                                      min_duration=chosen["min_duration"], merge_gap=chosen["merge_gap"])
        print(line("test (frozen)" if name == "test" else "fault-free recording", result))
    print(f"\nnormal hours needed to show a rate <= {BUDGET:.3f}/h at 95 % with zero false alarms: "
          f"{-math.log(0.05) / BUDGET:.1f} h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
