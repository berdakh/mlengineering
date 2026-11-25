"""Baseline table for the project on the REAL SKAB data.

    python project/get_skab.py                                        # once, from the repo root
    python labs/w2d6_baselines_metrics/lab/baseline_table.py       # prints the table

Protocol (identical for every row of the table):
* split by experiment (manifest from flowguard.splits.make_splits, seed 0);
* rows with t < BURN_IN are never evaluated, so global and burn-in methods are compared on the same rows;
* the decision threshold is the best-F1 threshold on DEV experiments; precision/recall/F1 are then
  reported on TEST experiments at that frozen threshold; PR-AUC needs no threshold.

This file is complete. It works once you have implemented flowguard.metrics, flowguard.baselines
and flowguard.benchmark.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import (ConstantScorer, MahalanobisScorer, MaxAbsZScorer,  # noqa: E402
                                 SingleSensorZScorer, burn_in_scores)
from flowguard.benchmark import evaluate_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.splits import dev_experiments, make_splits, validate_splits  # noqa: E402

BURN_IN = 100          # rows (about 100 s) at the start of each experiment used for calibration
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"


def burn_in_abs_z(tidy, n_burn: int) -> np.ndarray:
    """|z| of every sensor against the experiment's own first n_burn rows, clipped to [0, 20]."""
    columns = []
    for sensor in SENSOR_COLUMNS:
        columns.append(burn_in_scores(lambda s=sensor: SingleSensorZScorer(s), tidy, n_burn))
    return np.clip(np.column_stack(columns), 0.0, 20.0)


def supervised_scores(tidy, manifest: dict, n_burn: int) -> np.ndarray:
    """Logistic regression on burn-in |z| features, trained on labelled DEV experiments.

    DEV rows get out-of-fold scores (each dev fold is scored by a model that never saw it), so the
    threshold chosen on dev is not flattered by in-sample fitting. TEST rows are scored by a model
    refitted on all dev experiments.
    """
    features = burn_in_abs_z(tidy, n_burn)
    y = tidy["anomaly"].to_numpy()
    usable = tidy["t"].to_numpy() >= n_burn
    experiment = tidy["experiment_id"]
    scores = np.zeros(len(tidy))
    for fold in manifest["dev_folds"]:
        held_out = experiment.isin(fold).to_numpy()
        train = experiment.isin([e for e in dev_experiments(manifest) if e not in fold]).to_numpy() & usable
        model = LogisticRegression(max_iter=2000).fit(features[train], y[train])
        scores[held_out] = model.predict_proba(features[held_out])[:, 1]
    all_dev = experiment.isin(dev_experiments(manifest)).to_numpy() & usable
    is_test = experiment.isin(manifest["test"]).to_numpy()
    model = LogisticRegression(max_iter=2000).fit(features[all_dev], y[all_dev])
    scores[is_test] = model.predict_proba(features[is_test])[:, 1]
    return scores


def build_rows(tidy, manifest: dict) -> list[tuple[str, np.ndarray]]:
    reference = tidy[tidy["experiment_id"].isin(manifest["reference_normal"])]
    rng = np.random.default_rng(0)
    return [
        ("constant", ConstantScorer().fit(reference).score(tidy)),
        ("random", rng.random(len(tidy))),
        ("elapsed time t (no sensors)", tidy["t"].to_numpy(dtype=float)),
        ("flow_rate abs z, global reference", SingleSensorZScorer("flow_rate").fit(reference).score(tidy)),
        ("max abs z, global reference", MaxAbsZScorer().fit(reference).score(tidy)),
        ("Mahalanobis, global reference", MahalanobisScorer().fit(reference).score(tidy)),
        ("flow_rate abs z, burn-in", burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), tidy, BURN_IN)),
        ("max abs z, burn-in", burn_in_scores(MaxAbsZScorer, tidy, BURN_IN)),
        ("Mahalanobis, burn-in", burn_in_scores(MahalanobisScorer, tidy, BURN_IN)),
        ("logistic regression on burn-in abs z (supervised)", supervised_scores(tidy, manifest, BURN_IN)),
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Baseline table on SKAB.")
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = make_splits(tidy, seed=0)
    validate_splits(manifest, tidy)
    families = sorted(set(tidy.loc[tidy["experiment_id"].isin(manifest["test"]), "family"]))
    print(f"experiments: dev {len(dev_experiments(manifest))}, test {len(manifest['test'])}; "
          f"burn-in {BURN_IN} rows; threshold = best F1 on dev\n")
    header = ["baseline", "dev PR-AUC", "test PR-AUC", "test P", "test R", "test F1"] + [f"PR-AUC {f}" for f in families]
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    prevalence = None
    for name, scores in build_rows(tidy, manifest):
        r = evaluate_scores(tidy, scores, manifest, burn_in=BURN_IN)
        prevalence = r["test"]["prevalence"]
        cells = [name, f"{r['dev']['pr_auc']:.3f}", f"{r['test']['pr_auc']:.3f}", f"{r['test']['precision']:.3f}",
                 f"{r['test']['recall']:.3f}", f"{r['test']['f1']:.3f}"]
        cells += [f"{r['test_by_family'][f]['pr_auc']:.3f}" for f in families]
        print("| " + " | ".join(cells) + " |")
    print(f"\ntest prevalence of anomalous rows (t >= {BURN_IN}): {prevalence:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
