"""SYNTHETIC grouped data and instrumented estimators, for checks only.

Nothing here resembles SKAB. The frames are Gaussian noise with planted structure, built so that
the *procedure* (who is fitted on what, who is scored on what, what is reported) can be verified
exactly. The estimators do no learning: their score is a fixed function of the features, which makes
every expected value computable independently of the code under test.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

FEATURES = ["gid", "f0", "f1", "f2", "f3", "f4", "f5"]      # "gid" carries the group code as a number
CALLS: list[tuple[str, frozenset]] = []                      # ("fit" | "score", group codes seen)


def auc(y_true, scores) -> float:
    return float(roc_auc_score(y_true, scores))


def make_tidy(n_groups: int = 8, rows: int = 120, seed: int = 0, signal: dict | None = None,
              prevalence: float = 0.4) -> pd.DataFrame:
    """``n_groups`` groups named g00, g01, ... with ``rows`` rows each.

    ``signal`` maps a feature name to a shift (in standard deviations) added to positive rows.
    """
    rng = np.random.default_rng(seed)
    frames = []
    for g in range(n_groups):
        y = (rng.random(rows) < prevalence).astype(int)
        y[:2] = [0, 1]                                        # both classes present in every group
        x = rng.standard_normal((rows, 6))
        for name, shift in (signal or {}).items():
            x[:, int(name[1:])] += shift * y
        df = pd.DataFrame(x, columns=FEATURES[1:])
        df.insert(0, "gid", float(g))
        df.insert(0, "anomaly", y)
        df.insert(0, "t", np.arange(rows))
        df.insert(0, "family", "synthetic")
        df.insert(0, "experiment_id", f"g{g:02d}")
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def folds_of(n_groups: int, n_folds: int, start: int = 0) -> list[list[str]]:
    ids = [f"g{g:02d}" for g in range(start, start + n_groups)]
    return [ids[i::n_folds] for i in range(n_folds)]


class ColumnScorer:
    """Scores a row by one feature column. Records which groups it was fitted and scored on."""

    def __init__(self, column: str = "f0"):
        self.j = FEATURES.index(column)

    def fit(self, X, y):
        assert len(X) == len(y) and len(X) > 0, "fit called with empty or misaligned data"
        CALLS.append(("fit", frozenset(np.unique(X[:, 0]).astype(int).tolist())))
        return self

    def predict_proba(self, X):
        CALLS.append(("score", frozenset(np.unique(X[:, 0]).astype(int).tolist())))
        p = 1.0 / (1.0 + np.exp(-X[:, self.j]))
        return np.column_stack([1.0 - p, p])


class ProjectionScorer:
    """Scores a row by a random projection of f0..f5 chosen by ``seed``. Pure noise on noise data."""

    def __init__(self, seed: int = 0):
        self.w = np.random.default_rng(1000 + seed).standard_normal(6)

    def fit(self, X, y):
        return self

    def predict_proba(self, X):
        p = 1.0 / (1.0 + np.exp(-(X[:, 1:] @ self.w)))
        return np.column_stack([1.0 - p, p])


def fold_auc_table(tidy: pd.DataFrame, folds, columns) -> np.ndarray:
    """ORACLE: AUC of each column on each fold, computed without the code under test. [column, fold]"""
    out = np.zeros((len(columns), len(folds)))
    for i, c in enumerate(columns):
        for k, fold in enumerate(folds):
            part = tidy[tidy["experiment_id"].isin(fold)]
            out[i, k] = auc(part["anomaly"], part[c])
    return out


def oracle_nested(table: np.ndarray) -> tuple[list[float], list[int]]:
    """ORACLE for nested_estimate with ColumnScorer candidates and the 'max' rule."""
    scores, chosen = [], []
    for k in range(table.shape[1]):
        inner = np.delete(table, k, axis=1).mean(axis=1)
        best = int(np.argmax(inner))                          # first maximum = earliest trial
        chosen.append(best)
        scores.append(float(table[best, k]))
    return scores, chosen
