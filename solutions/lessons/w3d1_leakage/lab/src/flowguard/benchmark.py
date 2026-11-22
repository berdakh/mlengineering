"""Evaluate one score column under the split manifest: threshold from dev, report on test."""
from __future__ import annotations

import numpy as np
import pandas as pd

from flowguard.metrics import best_f1_threshold, f1_from, pr_auc, precision_recall_at_threshold
from flowguard.splits import dev_experiments


def _summary(y: np.ndarray, s: np.ndarray, threshold: float) -> dict:
    precision, recall = precision_recall_at_threshold(y, s, threshold)
    return {
        "n": int(len(y)), "prevalence": float(np.mean(y)) if len(y) else float("nan"),
        "pr_auc": pr_auc(y, s), "precision": precision, "recall": recall,
        "f1": f1_from(precision, recall),
    }


def evaluate_scores(tidy: pd.DataFrame, scores, manifest: dict, burn_in: int = 0) -> dict:
    """Choose the decision threshold on DEV experiments only, then report on TEST experiments.

    ``scores`` is aligned with the rows of ``tidy``. Rows with ``t < burn_in`` are excluded from
    both threshold selection and evaluation (they were used for per-experiment calibration).
    Returns ``{"threshold", "dev": {...}, "test": {...}, "test_by_family": {family: {...}}}``.
    """
    scores = np.asarray(scores, dtype=float)
    if len(scores) != len(tidy):
        raise ValueError("scores must have one value per row of tidy")
    y = tidy["anomaly"].to_numpy()
    usable = tidy["t"].to_numpy() >= burn_in
    is_dev = tidy["experiment_id"].isin(dev_experiments(manifest)).to_numpy() & usable
    is_test = tidy["experiment_id"].isin(manifest["test"]).to_numpy() & usable
    threshold, _ = best_f1_threshold(y[is_dev], scores[is_dev])
    family = tidy["family"].to_numpy()
    return {
        "threshold": threshold,
        "dev": _summary(y[is_dev], scores[is_dev], threshold),
        "test": _summary(y[is_test], scores[is_test], threshold),
        "test_by_family": {
            f: _summary(y[is_test & (family == f)], scores[is_test & (family == f)], threshold)
            for f in sorted(set(family[is_test]))
        },
    }
