"""What did the duplicated rows cost? Compare split v1 with its repair v2 on the REAL SKAB data.

    python project/get_skab.py                              # once, from the repo root
    python labs/w3d1_leakage/lab/v1_vs_v2.py             # prints the comparison
    python labs/w3d1_leakage/lab/v1_vs_v2.py --write     # also freezes splits/v2.json

This file is complete. It works once flowguard.splits (find_overlap_groups, repair_splits,
validate_splits) and flowguard.leakcheck (clock_probe) are implemented.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.baselines import SingleSensorZScorer, burn_in_scores  # noqa: E402
from flowguard.benchmark import evaluate_scores  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.leakcheck import clock_probe  # noqa: E402
from flowguard.splits import (dev_experiments, diff_manifests, find_overlap_groups, load_splits,  # noqa: E402
                              repair_splits, save_splits, validate_splits)

BURN_IN = 100
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
ROW_KEY = ["datetime", *SENSOR_COLUMNS]


def shared_rows(tidy: pd.DataFrame, side_a: list[str], side_b: list[str]) -> tuple[int, int]:
    """(rows of side_b that also occur in side_a, how many of those carry a different label)."""
    a = tidy[tidy["experiment_id"].isin(side_a)][[*ROW_KEY, "anomaly"]].drop_duplicates(ROW_KEY)
    b = tidy[tidy["experiment_id"].isin(side_b)][[*ROW_KEY, "anomaly"]]
    both = b.merge(a, on=ROW_KEY, suffixes=("_b", "_a"))
    return len(both), int((both["anomaly_a"] != both["anomaly_b"]).sum())


def burn_in_abs_z(tidy: pd.DataFrame) -> np.ndarray:
    cols = [burn_in_scores(lambda s=s: SingleSensorZScorer(s), tidy, BURN_IN) for s in SENSOR_COLUMNS]
    return np.clip(np.column_stack(cols), 0.0, 20.0)


def supervised_scores(tidy: pd.DataFrame, features: np.ndarray, manifest: dict) -> np.ndarray:
    """Logistic regression on burn-in |z|: out-of-fold scores on dev, a dev-trained model on test."""
    y = tidy["anomaly"].to_numpy()
    usable = tidy["t"].to_numpy() >= BURN_IN
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(REPO_ROOT / "data" / "raw" / "skab"))
    ap.add_argument("--write", action="store_true", help="write splits/v2.json next to this script")
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    v1 = load_splits(HERE / "splits" / "v1.json")
    groups = find_overlap_groups(tidy)
    print("overlap groups:", [sorted(g) for g in groups])
    try:
        validate_splits(v1, tidy)
        print("v1 passes validation (unexpected)")
    except ValueError as exc:
        print(f"v1 is rejected: {exc}")
    v2 = repair_splits(v1, groups)
    validate_splits(v2, tidy)
    print("\nmoved by the repair:")
    for exp, (old, new) in diff_manifests(v1, v2).items():
        print(f"  {exp:10s} {old} -> {new}")

    labelled = tidy[tidy["family"] != "anomaly-free"].reset_index(drop=True)
    features = burn_in_abs_z(labelled)
    flow = burn_in_scores(lambda: SingleSensorZScorer("flow_rate"), labelled, BURN_IN)
    print("\n| manifest | test experiments | test rows also in dev (contradictory labels) | "
          "flow_rate burn-in z: test PR-AUC | logistic regression: test PR-AUC | clock: test PR-AUC | test prevalence |")
    print("|---|---|---|---|---|---|---|")
    for name, m in (("v1", v1), ("v2", v2)):
        n_shared, n_conflict = shared_rows(labelled, dev_experiments(m), m["test"])
        r_flow = evaluate_scores(labelled, flow, m, burn_in=BURN_IN)
        r_lr = evaluate_scores(labelled, supervised_scores(labelled, features, m), m, burn_in=BURN_IN)
        clock = clock_probe(labelled, m["test"], burn_in=BURN_IN)
        print(f"| {name} | {len(m['test'])} | {n_shared} ({n_conflict}) | {r_flow['test']['pr_auc']:.3f} | "
              f"{r_lr['test']['pr_auc']:.3f} | {clock['pr_auc_clock']:.3f} | {clock['prevalence']:.3f} |")
    common = sorted(set(v1["test"]) & set(v2["test"]))
    same = dict(v2, test=common)
    r_lr_common_v1 = evaluate_scores(labelled, supervised_scores(labelled, features, dict(v1, test=common)), dict(v1, test=common), burn_in=BURN_IN)
    r_lr_common_v2 = evaluate_scores(labelled, supervised_scores(labelled, features, same), same, burn_in=BURN_IN)
    print(f"\nlogistic regression on the {len(common)} experiments that are test in both manifests: "
          f"v1 training {r_lr_common_v1['test']['pr_auc']:.3f}, v2 training {r_lr_common_v2['test']['pr_auc']:.3f}")
    probe = clock_probe(labelled)
    print(f"\nclock probe, all labelled experiments: PR-AUC {probe['pr_auc_clock']:.3f} against prevalence "
          f"{probe['prevalence']:.3f}; anomaly onset at t = {probe['onset_t_min']}..{probe['onset_t_max']} "
          f"(median {probe['onset_t_median']:.0f})")
    if args.write:
        save_splits(v2, HERE / "splits" / "v2.json")
        print(f"\nwrote {HERE / 'splits' / 'v2.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
