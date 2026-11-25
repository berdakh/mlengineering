"""Hyperparameter and threshold selection for a supervised detector on the REAL SKAB data.

    python project/get_skab.py                                               # once, from the repo root
    python labs/w3d3_hyperparameter_selection/lab/selection_report.py     # about 2-4 minutes on a laptop CPU
    python labs/w3d3_hyperparameter_selection/lab/selection_report.py --n-candidates 6   # quick look

What it does, in the order a defensible report needs:

1. splits by experiment (manifest v2: overlap groups kept together), features from past rows only;
2. random search over two model families with grouped 4-fold CV on the DEV experiments  -> all trials;
3. nested estimate of the whole procedure (search + select + refit)                      -> honest dev number;
4. threshold chosen on out-of-fold DEV scores of the selected candidate, then frozen;
5. ONE evaluation on the TEST experiments.

This file is complete. It works once flowguard.selection is implemented.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "splits" / "v2.json"  # frozen split manifest from w3d1
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import load_raw  # noqa: E402
from flowguard.features import all_feature_columns, columns_for, selection_features  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.selection import (frozen_threshold_evaluation, grouped_search, nested_estimate,  # noqa: E402
                                 sample_params, select_best)
from flowguard.splits import dev_experiments, load_splits, validate_splits  # noqa: E402

BURN_IN = 100   # rows at the start of each experiment used for normalisation; never fitted or scored
REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
DEFAULT_RAW = REPO_ROOT / "data" / "raw" / "skab"
ALL_COLUMNS = all_feature_columns()


class ColumnWindow:
    """Wraps an estimator so that ``window`` (which feature columns to use) is a hyperparameter."""

    def __init__(self, window: int, estimator):
        self.index = [ALL_COLUMNS.index(c) for c in columns_for(window)]
        self.estimator = estimator

    def fit(self, X, y):
        self.estimator.fit(X[:, self.index], y)
        return self

    def predict_proba(self, X):
        return self.estimator.predict_proba(X[:, self.index])


def make_model(model: str, window: int, C: float = 1.0, max_depth: int = 3, learning_rate: float = 0.1,
               max_iter: int = 100):
    if model == "logreg":
        return ColumnWindow(window, make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000)))
    if model == "hgb":
        return ColumnWindow(window, HistGradientBoostingClassifier(
            max_depth=max_depth, learning_rate=learning_rate, max_iter=max_iter, random_state=0))
    raise ValueError(model)


def complexity(params: dict) -> float:
    """Ordering used by the one-standard-error rule: linear before boosted, short windows before long,
    then stronger regularisation / fewer and shallower trees first."""
    if params["model"] == "logreg":
        return 0.0 + params["window"] / 1000 + np.log10(params["C"]) / 1e6
    return 1.0 + params["window"] / 1000 + params["max_depth"] * params["max_iter"] / 1e7


def candidates(n: int, seed: int) -> list[dict]:
    half = n // 2
    logreg = sample_params({"model": ("choice", ["logreg"]), "window": ("choice", [0, 10, 30, 60]),
                            "C": ("loguniform", 1e-3, 1e2)}, half, seed)
    hgb = sample_params({"model": ("choice", ["hgb"]), "window": ("choice", [0, 10, 30, 60]),
                         "max_depth": ("int", 2, 6), "learning_rate": ("loguniform", 0.02, 0.3),
                         "max_iter": ("choice", [50, 100, 200])}, n - half, seed + 1)
    return logreg + hgb


def out_of_fold_scores(params: dict, feats, folds) -> np.ndarray:
    """Dev scores where every row is scored by a model that never saw its experiment."""
    X, y = feats[ALL_COLUMNS].to_numpy(), feats["anomaly"].to_numpy()
    scores = np.full(len(feats), np.nan)
    for k, fold in enumerate(folds):
        train = feats["experiment_id"].isin([e for j, f in enumerate(folds) if j != k for e in f]).to_numpy()
        held = feats["experiment_id"].isin(fold).to_numpy()
        scores[held] = make_model(**params).fit(X[train], y[train]).predict_proba(X[held])[:, 1]
    return scores


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw-dir", default=str(DEFAULT_RAW))
    ap.add_argument("--n-candidates", type=int, default=24)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=str(HERE / "runs" / "selection"))
    args = ap.parse_args(argv)
    try:
        tidy = load_raw(args.raw_dir)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(MANIFEST)  # v2, frozen in w3d1; never redrawn (the test set is fixed once results have been seen)
    validate_splits(manifest, tidy)
    feats = selection_features(tidy, BURN_IN)
    feats = feats[feats["t"] >= BURN_IN].reset_index(drop=True)          # burn-in rows are never used
    folds = manifest["dev_folds"]
    cands = candidates(args.n_candidates, args.seed)
    print(f"dev experiments {len(dev_experiments(manifest))} in {len(folds)} folds, test {len(manifest['test'])}; "
          f"{len(cands)} candidates; metric = point-level PR-AUC")

    t0 = time.perf_counter()
    trials = grouped_search(make_model, cands, feats, folds, pr_auc, ALL_COLUMNS)
    best = select_best(trials, "max")
    simple = select_best(trials, "one_se", complexity)
    t_search = time.perf_counter() - t0
    means = np.array([t["mean"] for t in trials])
    print(f"\nsearch ({t_search:.0f} s): dev CV PR-AUC over candidates: min {means.min():.3f}, "
          f"median {np.median(means):.3f}, max {means.max():.3f}")
    print(f"  best trial    #{best['trial']}: {best['mean']:.3f} +/- {best['se']:.3f} (SE over folds)  {best['params']}")
    print(f"  one-SE choice #{simple['trial']}: {simple['mean']:.3f} +/- {simple['se']:.3f}  {simple['params']}")

    t0 = time.perf_counter()
    nested = nested_estimate(make_model, cands, feats, folds, pr_auc, ALL_COLUMNS, rule="one_se", complexity=complexity)
    t_nested = time.perf_counter() - t0
    print(f"\nnested estimate of search + one-SE selection + refit ({t_nested:.0f} s): "
          f"{nested['mean']:.3f} +/- {nested['se']:.3f}")
    for k, (score, inner, params) in enumerate(zip(nested["outer_scores"], nested["inner_best"], nested["chosen_params"])):
        print(f"  outer fold {k}: inner selected mean {inner:.3f} -> outer score {score:.3f}  {params}")

    # threshold: out-of-fold dev scores of the selected candidate, then one frozen test evaluation
    dev_rows = feats["experiment_id"].isin(dev_experiments(manifest)).to_numpy()
    test_rows = feats["experiment_id"].isin(manifest["test"]).to_numpy()
    X, y = feats[ALL_COLUMNS].to_numpy(), feats["anomaly"].to_numpy()
    oof = out_of_fold_scores(simple["params"], feats, folds)
    final = make_model(**simple["params"]).fit(X[dev_rows], y[dev_rows])
    test_scores = final.predict_proba(X[test_rows])[:, 1]
    print(f"\nTEST (looked at once), selected candidate refitted on all dev experiments:")
    print(f"  test PR-AUC {pr_auc(y[test_rows], test_scores):.3f}   "
          f"(dev CV of the selected trial {simple['mean']:.3f}, best dev CV of any trial {best['mean']:.3f}, "
          f"nested {nested['mean']:.3f})")
    clock = feats["t"].to_numpy(dtype=float)
    report = {"n_candidates": len(cands), "seed": args.seed, "trials": trials, "best": best, "one_se": simple,
              "nested": nested, "test_pr_auc": pr_auc(y[test_rows], test_scores),
              "clock_test_pr_auc": pr_auc(y[test_rows], clock[test_rows]),
              "seconds": {"search": round(t_search, 1), "nested": round(t_nested, 1)}, "thresholds": {}}
    for rule, budget in (("best_f1", None), ("alert_budget", 0.05)):
        r = frozen_threshold_evaluation(oof[dev_rows], y[dev_rows], test_scores, y[test_rows], rule, budget)
        report["thresholds"][rule] = r
        label = rule if budget is None else f"{rule} {budget:.0%}"
        print(f"  threshold [{label}] = {r['threshold']:.3f}:  dev P {r['dev']['precision']:.3f} R {r['dev']['recall']:.3f} "
              f"F1 {r['dev']['f1']:.3f} FAR {r['dev']['false_alarm_rate']:.3f} | test P {r['test']['precision']:.3f} "
              f"R {r['test']['recall']:.3f} F1 {r['test']['f1']:.3f} FAR {r['test']['false_alarm_rate']:.3f}")
    print(f"\nfor scale: elapsed time alone (no sensors) has test PR-AUC {report['clock_test_pr_auc']:.3f}; "
          f"test prevalence {y[test_rows].mean():.3f}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "selection_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"all {len(trials)} trials written to {out / 'selection_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
