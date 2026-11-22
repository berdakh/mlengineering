"""Error-analysis tables for the w2d6 bar baseline on the REAL SKAB data (development experiments only).

    python project/get_skab.py                                              # once, from the repo root
    python lessons/w3d6_error_analysis_transfer/lab/error_report.py         # prints the tables

Baseline analysed: |z| of flow_rate against each experiment's own first BURN_IN rows (the bar set in
w2d6). The threshold is the best-F1 threshold on the development experiments. The TEST experiments
are never scored here: analysing test errors and then changing the model would turn the test set
into a second development set.

This file is complete. It works once you have implemented flowguard.erroranalysis.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"  # frozen split manifest from w3d1
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.erroranalysis import (error_segments, per_experiment_table, slice_metrics,  # noqa: E402
                                     summarise_segments)
from flowguard.metrics import best_f1_threshold  # noqa: E402
from flowguard.splits import dev_experiments, find_overlap_groups, load_splits, validate_splits  # noqa: E402

BURN_IN = 100
LATE_AFTER = 30
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


def slicing_columns(dev: pd.DataFrame, groups: list[set[str]]) -> pd.DataFrame:
    """Per-experiment attributes to slice by. Each is computable without looking at the scores."""
    shared = {e for g in groups for e in g}
    rows = []
    for experiment_id, g in dev.groupby("experiment_id", sort=False):
        g = g.sort_values("t")
        gap = g["datetime"].diff().dt.total_seconds().max()
        burn = g[g["t"] < BURN_IN]
        normal = g[g["anomaly"] == 0]
        anomalous = g[g["anomaly"] == 1]
        shift = abs(anomalous["flow_rate"].mean() - normal["flow_rate"].mean()) / max(normal["flow_rate"].std(), 1e-9)
        rows.append({
            "experiment_id": experiment_id,
            "has_gap": "gap > 5 s" if gap > 5 else "no gap",
            "shares_rows": "shares rows" if experiment_id in shared else "unique rows",
            "burn_in_flow": "low flow (< 60)" if burn["flow_rate"].mean() < 60 else "high flow (>= 60)",
            "flow_shift_sd": float(shift),
            "flow_shift": "flow moves >= 1 sd" if shift >= 1 else "flow moves < 1 sd",
        })
    return pd.DataFrame(rows)


def show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n## {title}\n")
    print(frame.to_string(index=False, float_format=lambda v: f"{v:.3f}"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    args = parser.parse_args()
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    groups = find_overlap_groups(tidy)
    manifest = load_splits(MANIFEST)  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    validate_splits(manifest, tidy)
    dev = tidy[tidy["experiment_id"].isin(dev_experiments(manifest))].reset_index(drop=True)
    scores = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), dev, BURN_IN)
    labels = dev["anomaly"].to_numpy()
    usable = dev["t"].to_numpy() >= BURN_IN
    threshold, f1 = best_f1_threshold(labels[usable], scores[usable])
    print(f"manifest v2, seed 0: {len(manifest['test'])} test (untouched), "
          f"{dev['experiment_id'].nunique()} development experiments")
    print(f"baseline: flow_rate abs z, burn-in {BURN_IN}; threshold {threshold:.3f} (dev F1 {f1:.3f})")

    table = per_experiment_table(scores, labels, threshold, dev, burn_in=BURN_IN)
    table = table.merge(slicing_columns(dev, groups), on="experiment_id")
    show("Per-experiment table, worst recall first",
         table.sort_values("recall")[["experiment_id", "n_pos", "recall", "precision", "false_alarm_rate",
                                      "onset_t", "detection_delay", "flow_shift_sd"]])
    for by in ("family", "has_gap", "shares_rows", "burn_in_flow", "flow_shift"):
        show(f"Recall by {by} (mean over experiments)", slice_metrics(table, by, "recall"))
    show("False-alarm rate by family", slice_metrics(table, "family", "false_alarm_rate"))

    segments = error_segments(scores, labels, threshold, dev, late_after=LATE_AFTER, burn_in=BURN_IN)
    show("Failure kinds", summarise_segments(segments))
    show("Largest error segments", segments.sort_values("n_rows", ascending=False).head(12))
    pooled = table["tp"].sum() / (table["tp"].sum() + table["fn"].sum())
    print(f"\nrow-pooled recall {pooled:.3f}; mean of per-experiment recalls {table['recall'].mean():.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
