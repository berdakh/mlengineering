"""How much does the skew matter? Score the 7 REAL test experiments with the training path and with
serve_scores.py, at the logistic candidate's operating point from w4d5.

    python project/get_skab.py                                              # once
    python lessons/w5d1_inference_pipeline/challenge/skew_on_real_data.py   # a few seconds

Given complete. Run it before and after your fixes.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "lab" / "src")]

from serve_scores import score_run  # noqa: E402
from train_features import training_scores  # noqa: E402

from flowguard.data import load_raw  # noqa: E402
from flowguard.evaluation import evaluate_experiments  # noqa: E402
from flowguard.metrics import pr_auc  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), HERE)
OPERATING_POINT = {"threshold": 3.964503, "min_duration": 30, "merge_gap": 10}   # w4d5 decision table, logistic row
N_BURN = 100


def scores_for(test, fn, model):
    out = np.full(len(test), np.nan)
    for _, g in test.groupby("experiment_id", sort=False):
        g = g.sort_values("t", kind="stable")
        s = fn(g, model)
        idx = g.index.to_numpy()[len(g) - len(s):]           # the scored rows are the run's last len(s) rows
        out[idx] = s
    return out


def summary(name, test, scores):
    keep = (test["t"].to_numpy() >= N_BURN) & ~np.isnan(scores)
    flagged = np.nan_to_num(scores, nan=-np.inf) >= OPERATING_POINT["threshold"]
    ev = evaluate_experiments(test, flagged, burn_in=N_BURN, min_duration=OPERATING_POINT["min_duration"],
                              merge_gap=OPERATING_POINT["merge_gap"])
    delay = "missed" if math.isinf(ev["median_delay_s"]) else f"{ev['median_delay_s']:.0f} s"
    print(f"  {name:<24} PR-AUC {pr_auc(test['anomaly'].to_numpy()[keep], scores[keep]):.3f}; events "
          f"{ev['n_detected']}/{ev['n_events']}; false alarms/h {ev['false_alarms_per_hour']:.2f}; median delay {delay}")
    return flagged


def main() -> int:
    try:
        tidy = load_raw(REPO_ROOT / "data" / "raw" / "skab")
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    manifest = load_splits(HERE.parent / "lab" / "splits" / "v2.json")
    test = tidy[tidy["experiment_id"].isin(manifest["test"])].reset_index(drop=True)
    model = json.loads((HERE / "model" / "logistic.json").read_text())
    trained = scores_for(test, training_scores, model)
    served = scores_for(test, score_run, model)
    both = ~np.isnan(trained) & ~np.isnan(served)
    print(f"rows scored: training path {int((~np.isnan(trained)).sum())}, serving path {int((~np.isnan(served)).sum())}")
    print(f"max |served - trained| on rows both score: {np.abs(served[both] - trained[both]).max():.3g}")
    print(f"test experiments ({len(manifest['test'])}), w4d5 operating point for the logistic candidate:")
    a = summary("training path", test, trained)
    b = summary("serving path", test, served)
    print(f"rows whose alarm decision differs: {int((a != b).sum())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
