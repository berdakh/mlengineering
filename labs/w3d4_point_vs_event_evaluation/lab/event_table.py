"""Point-level versus event-level results for the w2d6 baselines on the REAL SKAB data.

    python project/get_skab.py                                              # once, from the repo root
    python labs/w3d4_point_vs_event_evaluation/lab/event_table.py
    python labs/w3d4_point_vs_event_evaluation/lab/event_table.py --min-duration 5 --merge-gap 10

Protocol (identical for every row):
* split by experiment, manifest v2 (experiments that share rows stay together), seed 0;
* rows with t < BURN_IN are never evaluated;
* the decision threshold is the best point-F1 threshold on DEV experiments, frozen for TEST;
* alarms = runs of flagged rows after the post-processing given on the command line;
* event metrics use flowguard.evaluation (start-based matching, early tolerance 0).

This file is complete. It works once flowguard.evaluation is implemented.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"  # frozen split manifest from w3d1
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import (MahalanobisScorer, MaxAbsZScorer, SingleSensorZScorer,  # noqa: E402
                                 burn_in_scores)
from flowguard.benchmark import evaluate_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments, extract_events, point_adjust  # noqa: E402
from flowguard.metrics import f1_from, precision_recall_at_threshold  # noqa: E402
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

BURN_IN = 100
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


def supervised_scores(tidy, manifest: dict, n_burn: int) -> np.ndarray:
    """Logistic regression on burn-in |z|; dev rows are scored out of fold, test rows by a dev-fitted model."""
    features = np.clip(np.column_stack(
        [burn_in_scores(lambda s=s: SingleSensorZScorer(s), tidy, n_burn) for s in SENSOR_COLUMNS]), 0.0, 20.0)
    y = tidy["anomaly"].to_numpy()
    usable = tidy["t"].to_numpy() >= n_burn
    experiment = tidy["experiment_id"]
    scores = np.zeros(len(tidy))
    for fold in manifest["dev_folds"]:
        held_out = experiment.isin(fold).to_numpy()
        train = experiment.isin([e for e in dev_experiments(manifest) if e not in fold]).to_numpy() & usable
        scores[held_out] = LogisticRegression(max_iter=2000).fit(features[train], y[train]).predict_proba(features[held_out])[:, 1]
    all_dev = experiment.isin(dev_experiments(manifest)).to_numpy() & usable
    is_test = experiment.isin(manifest["test"]).to_numpy()
    scores[is_test] = LogisticRegression(max_iter=2000).fit(features[all_dev], y[all_dev]).predict_proba(features[is_test])[:, 1]
    return scores


def build_rows(tidy, manifest: dict) -> list[tuple[str, np.ndarray]]:
    rng = np.random.default_rng(0)
    return [
        ("random", rng.random(len(tidy))),
        ("elapsed time t (no sensors)", tidy["t"].to_numpy(dtype=float)),
        ("flow_rate abs z, burn-in", burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)),
        ("max abs z, burn-in", burn_in_scores(MaxAbsZScorer, tidy, BURN_IN)),
        ("Mahalanobis, burn-in", burn_in_scores(MahalanobisScorer, tidy, BURN_IN)),
        ("logistic regression (supervised)", supervised_scores(tidy, manifest, BURN_IN)),
    ]


def point_adjusted_f1(test, flagged: np.ndarray) -> float:
    """Point F1 after applying point-adjust within each test experiment (for demonstration only)."""
    y = test["anomaly"].to_numpy()
    adjusted = flagged.copy()
    for _, idx in test.groupby("experiment_id", sort=False).indices.items():
        adjusted[idx] = point_adjust(y[idx], flagged[idx])
    tp = int(np.sum((adjusted == 1) & (y == 1)))
    precision = tp / int(adjusted.sum()) if adjusted.any() else 0.0
    recall = tp / int(y.sum())
    return f1_from(precision, recall)


def fmt(x: float, digits: int = 0) -> str:
    return "missed" if math.isinf(x) else "-" if math.isnan(x) else f"{x:.{digits}f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Point versus event evaluation on SKAB.")
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--min-duration", type=int, default=1, help="drop alarms shorter than this many rows")
    ap.add_argument("--merge-gap", type=int, default=0, help="merge alarms separated by this many rows or fewer")
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    validate_splits(manifest, tidy)
    in_test = (tidy["experiment_id"].isin(manifest["test"]) & (tidy["t"] >= BURN_IN)).to_numpy()
    test = tidy[in_test].reset_index(drop=True)
    true_rows = int(test["anomaly"].sum())
    n_true = sum(len(extract_events(g["anomaly"].to_numpy())) for _, g in test.groupby("experiment_id", sort=False))
    print(f"experiments: dev {len(dev_experiments(manifest))}, test {len(manifest['test'])} "
          f"({', '.join(manifest['test'])})")
    print(f"test rows evaluated: {len(test)} ({true_rows} anomalous, {n_true} events); burn-in {BURN_IN} rows; "
          f"min_duration={args.min_duration}, merge_gap={args.merge_gap}\n")
    header = ["detector", "point P", "point R", "point F1", "F1 after point-adjust", "events found",
              "alarms", "false alarms", "redundant", "event P", "false alarms / h", "median delay s", "p90 delay s"]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    hours = float("nan")
    for name, scores in build_rows(tidy, manifest):
        threshold = evaluate_scores(tidy, scores, manifest, burn_in=BURN_IN)["threshold"]
        flagged = (scores[in_test] >= threshold).astype(int)
        p, r = precision_recall_at_threshold(test["anomaly"].to_numpy(), scores[in_test], threshold)
        ev = evaluate_experiments(test, flagged, min_duration=args.min_duration, merge_gap=args.merge_gap)
        hours = ev["normal_hours"]
        cells = [name, f"{p:.3f}", f"{r:.3f}", f"{f1_from(p, r):.3f}", f"{point_adjusted_f1(test, flagged):.3f}",
                 f"{ev['n_detected']}/{ev['n_events']}", str(ev["n_alarms"]), str(ev["n_false_alarms"]),
                 str(ev["n_redundant"]), fmt(ev["event_precision"], 3), fmt(ev["false_alarms_per_hour"], 1),
                 fmt(ev["median_delay_s"]), fmt(ev["p90_delay_s"])]
        print("| " + " | ".join(cells) + " |")
    print(f"\nnormal operation in the evaluated test rows: {hours:.2f} h (wall clock, gaps included)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
