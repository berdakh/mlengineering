"""Point-level metrics. One row = one timestamp. Higher score = more anomalous.

Conventions (the checks rely on them):
* a row is flagged when ``score >= threshold``;
* precision is 0.0 when nothing is flagged, recall is 0.0 when there are no positives;
* ``pr_auc`` is average precision (step-wise area), NaN when there are no positives.
"""
from __future__ import annotations

import numpy as np


def _as_arrays(y_true, scores) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(y_true).astype(int).ravel()
    s = np.asarray(scores, dtype=float).ravel()
    if y.shape != s.shape:
        raise ValueError(f"y_true and scores differ in length: {y.shape} vs {s.shape}")
    if not np.isfinite(s).all():
        raise ValueError("scores must be finite")
    return y, s


def _curve(y: np.ndarray, s: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Thresholds (descending, distinct) with TP and FP counts when flagging score >= threshold."""
    order = np.argsort(-s, kind="stable")
    y, s = y[order], s[order]
    last_of_tie = np.r_[np.nonzero(np.diff(s))[0], len(s) - 1]   # tied scores enter together
    tp = np.cumsum(y)[last_of_tie]
    fp = (last_of_tie + 1) - tp
    return s[last_of_tie], tp, fp


def pr_auc(y_true, scores) -> float:
    """Average precision: sum over thresholds of (recall_k - recall_{k-1}) * precision_k."""
    y, s = _as_arrays(y_true, scores)
    n_pos = int(y.sum())
    if n_pos == 0:
        return float("nan")
    _, tp, fp = _curve(y, s)
    precision = tp / (tp + fp)
    recall = tp / n_pos
    return float(np.sum(np.diff(np.r_[0.0, recall]) * precision))


def precision_recall_at_threshold(y_true, scores, threshold: float) -> tuple[float, float]:
    y, s = _as_arrays(y_true, scores)
    flagged = s >= threshold
    tp = int(np.sum(flagged & (y == 1)))
    precision = tp / int(flagged.sum()) if flagged.any() else 0.0
    recall = tp / int(y.sum()) if y.any() else 0.0
    return float(precision), float(recall)


def f1_from(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def best_f1_threshold(y_true, scores) -> tuple[float, float]:
    """(threshold, f1) maximising F1 over the observed score values. Ties: the highest threshold."""
    y, s = _as_arrays(y_true, scores)
    n_pos = int(y.sum())
    thresholds, tp, fp = _curve(y, s)
    if n_pos == 0:
        return float(thresholds[0]), 0.0
    f1 = 2 * tp / (2 * tp + fp + (n_pos - tp))
    best = int(np.argmax(f1))                 # argmax returns the first = highest threshold
    return float(thresholds[best]), float(f1[best])
