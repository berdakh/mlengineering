"""Point-level metrics. One row = one timestamp. Higher score = more anomalous.

Conventions (the checks rely on them):
* a row is flagged when ``score >= threshold``;
* precision is 0.0 when nothing is flagged, recall is 0.0 when there are no positives;
* ``pr_auc`` is average precision (step-wise area), NaN when there are no positives;
* inputs of different length raise ValueError.

Implement these with NumPy. Do not call scikit-learn here: the point of the lab is that you can
state exactly what each number is. (The checks compare your results with scikit-learn.)
"""
from __future__ import annotations


def pr_auc(y_true, scores) -> float:
    """Average precision: sum over thresholds k of (recall_k - recall_{k-1}) * precision_k.

    Rows with tied scores cross the threshold together: they form ONE step of the curve.
    """
    raise NotImplementedError("lab task 2")


def precision_recall_at_threshold(y_true, scores, threshold: float) -> tuple[float, float]:
    """(precision, recall) when rows with score >= threshold are flagged."""
    raise NotImplementedError("lab task 2")


def f1_from(precision: float, recall: float) -> float:
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def best_f1_threshold(y_true, scores) -> tuple[float, float]:
    """(threshold, f1): the threshold among the observed score values that maximises F1."""
    raise NotImplementedError("lab task 2")
