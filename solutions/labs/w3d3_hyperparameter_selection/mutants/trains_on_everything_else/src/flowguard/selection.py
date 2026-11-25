"""Hyperparameter and threshold selection that never touches the data used to report a result.

Vocabulary used throughout:

* a *candidate* is one dict of hyperparameters;
* a *trial* is the record of evaluating one candidate: its per-fold validation scores;
* ``folds`` is a list of lists of group ids (the ``dev_folds`` of a split manifest). Rows whose group
  is in none of the folds (test experiments, reference recordings) are never fitted and never scored.

Estimator contract: ``estimator_factory(**params)`` returns a fresh object with ``fit(X, y)`` and
``predict_proba(X)``; the score of a row is ``predict_proba(X)[:, 1]`` (higher = more anomalous).
"""
from __future__ import annotations

import itertools
import math
from typing import Callable, Mapping, Sequence

import numpy as np
import pandas as pd

Trial = dict  # {"trial": int, "params": dict, "fold_scores": list[float], "mean": float, "se": float}


# ----------------------------------------------------------------------------- candidates
def param_grid(grid: Mapping[str, Sequence]) -> list[dict]:
    """Cartesian product of the listed values, in a deterministic order."""
    names = list(grid)
    return [dict(zip(names, values)) for values in itertools.product(*(grid[n] for n in names))]


def sample_params(space: Mapping[str, tuple], n: int, seed: int) -> list[dict]:
    """``n`` random candidates. Each entry of ``space`` is one of

    ``("loguniform", low, high)``, ``("uniform", low, high)``, ``("int", low, high)`` (inclusive)
    or ``("choice", [values...])``. The same seed always gives the same list.
    """
    rng = np.random.default_rng(seed)
    candidates = []
    for _ in range(n):
        params = {}
        for name, spec in space.items():
            kind = spec[0]
            if kind == "loguniform":
                params[name] = float(math.exp(rng.uniform(math.log(spec[1]), math.log(spec[2]))))
            elif kind == "uniform":
                params[name] = float(rng.uniform(spec[1], spec[2]))
            elif kind == "int":
                params[name] = int(rng.integers(spec[1], spec[2] + 1))
            elif kind == "choice":
                params[name] = spec[1][int(rng.integers(len(spec[1])))]
            else:
                raise ValueError(f"unknown distribution {kind!r} for parameter {name!r}")
        candidates.append(params)
    return candidates


# ----------------------------------------------------------------------------- search
def _rows_of(tidy: pd.DataFrame, groups: Sequence[str], group_column: str) -> np.ndarray:
    return tidy[group_column].isin(list(groups)).to_numpy()


def _fit_and_score(factory: Callable, params: dict, tidy: pd.DataFrame, train_groups: Sequence[str],
                   eval_groups: Sequence[str], metric: Callable, feature_columns: Sequence[str],
                   label_column: str, group_column: str) -> float:
    features = tidy[list(feature_columns)].to_numpy()
    labels = tidy[label_column].to_numpy()
    held_out = _rows_of(tidy, eval_groups, group_column)
    train = ~held_out                                     # "everything that is not validation"
    model = factory(**params)
    model.fit(features[train], labels[train])
    return float(metric(labels[held_out], model.predict_proba(features[held_out])[:, 1]))


def grouped_search(estimator_factory: Callable, candidates: Sequence[dict], tidy: pd.DataFrame,
                   folds: Sequence[Sequence[str]], metric: Callable, feature_columns: Sequence[str],
                   label_column: str = "anomaly", group_column: str = "experiment_id") -> list[Trial]:
    """Evaluate every candidate by grouped cross-validation over ``folds``. Returns ALL trials.

    For fold k the model is fitted on the rows of the other folds and scored on the rows of fold k.
    Rows outside ``folds`` are not used at all.
    """
    if len(folds) < 2:
        raise ValueError("grouped_search needs at least two folds")
    trials: list[Trial] = []
    for i, params in enumerate(candidates):
        scores = []
        for k, fold in enumerate(folds):
            train_groups = [g for j, other in enumerate(folds) if j != k for g in other]
            scores.append(_fit_and_score(estimator_factory, params, tidy, train_groups, fold, metric,
                                         feature_columns, label_column, group_column))
        se = float(np.std(scores, ddof=1) / math.sqrt(len(scores)))
        trials.append({"trial": i, "params": dict(params), "fold_scores": scores,
                       "mean": float(np.mean(scores)), "se": se})
    return trials


def select_best(trials: Sequence[Trial], rule: str = "max", complexity: Callable[[dict], float] | None = None) -> Trial:
    """Pick one trial.

    ``"max"``: highest mean score (ties: the earliest trial).
    ``"one_se"``: among trials whose mean is within one standard error (the best trial's SE) of the
    best mean, the one with the lowest ``complexity(params)`` (ties: higher mean, then earlier trial).
    """
    if not trials:
        raise ValueError("no trials to select from")
    best = max(trials, key=lambda t: (t["mean"], -t["trial"]))
    if rule == "max":
        return best
    if rule == "one_se":
        if complexity is None:
            raise ValueError("the one_se rule needs a complexity function")
        eligible = [t for t in trials if t["mean"] >= best["mean"] - best["se"]]
        return min(eligible, key=lambda t: (complexity(t["params"]), -t["mean"], t["trial"]))
    raise ValueError(f"unknown rule {rule!r}")


def nested_estimate(estimator_factory: Callable, candidates: Sequence[dict], tidy: pd.DataFrame,
                    folds: Sequence[Sequence[str]], metric: Callable, feature_columns: Sequence[str],
                    label_column: str = "anomaly", group_column: str = "experiment_id",
                    rule: str = "max", complexity: Callable[[dict], float] | None = None) -> dict:
    """Estimate the performance of the whole procedure "search, select, refit".

    For each outer fold k: run the search on the remaining folds only, select, refit the selected
    candidate on all remaining folds, score on fold k. Fold k plays no part in choosing its model.
    """
    if len(folds) < 3:
        raise ValueError("nested_estimate needs at least three folds (two must remain for the inner search)")
    outer_scores, chosen, inner_best = [], [], []
    for k, outer in enumerate(folds):
        inner_folds = [fold for j, fold in enumerate(folds) if j != k]
        trials = grouped_search(estimator_factory, candidates, tidy, inner_folds, metric,
                                feature_columns, label_column, group_column)
        winner = select_best(trials, rule, complexity)
        inner_groups = [g for fold in inner_folds for g in fold]
        outer_scores.append(_fit_and_score(estimator_factory, winner["params"], tidy, inner_groups, outer,
                                           metric, feature_columns, label_column, group_column))
        chosen.append(dict(winner["params"]))
        inner_best.append(winner["mean"])
    return {
        "outer_scores": outer_scores,
        "mean": float(np.mean(outer_scores)),
        "se": float(np.std(outer_scores, ddof=1) / math.sqrt(len(outer_scores))),
        "chosen_params": chosen,
        "inner_best": inner_best,
    }


# ----------------------------------------------------------------------------- thresholds
def _prf(labels: np.ndarray, flagged: np.ndarray) -> dict:
    tp = int(np.sum(flagged & (labels == 1)))
    precision = tp / int(flagged.sum()) if flagged.any() else 0.0
    recall = tp / int((labels == 1).sum()) if (labels == 1).any() else 0.0
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    normal = labels == 0
    return {"precision": float(precision), "recall": float(recall), "f1": float(f1),
            "false_alarm_rate": float(np.mean(flagged[normal])) if normal.any() else 0.0}


def evaluate_at_threshold(scores, labels, threshold: float) -> dict:
    """Precision, recall, F1 and false-alarm rate when rows with ``score >= threshold`` are flagged."""
    scores = np.asarray(scores, dtype=float)
    labels = np.asarray(labels).astype(int)
    return _prf(labels, scores >= threshold)


def select_threshold(dev_scores, dev_labels, rule: str = "best_f1", budget: float | None = None) -> float:
    """Choose a decision threshold from DEVELOPMENT scores only. A row is flagged when score >= threshold.

    ``"best_f1"``: the observed score value maximising F1 (ties: the highest threshold).
    ``"alert_budget"``: the lowest observed score value at which the fraction of normal (label 0)
    rows flagged is at most ``budget``; if no observed value satisfies it, a value just above the
    maximum score (nothing is flagged).
    """
    scores = np.asarray(dev_scores, dtype=float)
    labels = np.asarray(dev_labels).astype(int)
    if scores.shape != labels.shape or scores.size == 0:
        raise ValueError("dev_scores and dev_labels must be non-empty and of equal length")
    values = np.unique(scores)[::-1]                      # descending candidate thresholds
    if rule == "best_f1":
        f1 = [_prf(labels, scores >= v)["f1"] for v in values]
        return float(values[int(np.argmax(f1))])          # first maximum = highest threshold
    if rule == "alert_budget":
        if budget is None or not 0.0 <= budget <= 1.0:
            raise ValueError("alert_budget needs a budget between 0 and 1")
        normal = np.sort(scores[labels == 0])
        chosen = float(np.nextafter(values[0], np.inf))
        for v in values:                                   # walk down while the budget holds
            flagged_normal = (len(normal) - np.searchsorted(normal, v, side="left")) / max(len(normal), 1)
            if flagged_normal > budget:
                break
            chosen = float(v)
        return chosen
    raise ValueError(f"unknown rule {rule!r}")


def frozen_threshold_evaluation(dev_scores, dev_labels, test_scores, test_labels,
                                rule: str = "best_f1", budget: float | None = None) -> dict:
    """Choose the threshold on dev, freeze it, and report dev and test metrics at that threshold."""
    threshold = select_threshold(dev_scores, dev_labels, rule, budget)
    return {"threshold": threshold, "rule": rule,
            "dev": evaluate_at_threshold(dev_scores, dev_labels, threshold),
            "test": evaluate_at_threshold(test_scores, test_labels, threshold)}
