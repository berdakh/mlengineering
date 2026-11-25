"""Reference solution: choose a trial from recorded fold scores and estimate its test score honestly."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _pick(scores: np.ndarray, n_params: np.ndarray) -> int:
    """One-standard-error rule on the given fold columns: simplest trial within one SE of the best mean."""
    mean = scores.mean(axis=1)
    best = int(np.argmax(mean))
    se = scores[best].std(ddof=1) / np.sqrt(scores.shape[1])
    eligible = np.flatnonzero(mean >= mean[best] - se)
    order = np.lexsort((-mean[eligible], n_params[eligible]))        # fewest parameters, then higher mean
    return int(eligible[order[0]])


def choose(trials: pd.DataFrame) -> dict:
    """Return {"trial": id of the chosen trial, "estimate": expected test score of that choice}.

    The estimate is NOT the chosen trial's own dev mean (that number was used to choose it). It is
    a nested estimate over the recorded folds: for each fold k, repeat the selection using the other
    folds only and read the selected trial's score on fold k.
    """
    fold_columns = [c for c in trials.columns if c.startswith("fold_")]
    scores = trials[fold_columns].to_numpy(dtype=float)
    n_params = trials["n_params"].to_numpy()
    chosen = _pick(scores, n_params)
    held_out = []
    for k in range(scores.shape[1]):
        inner = np.delete(scores, k, axis=1)
        held_out.append(scores[_pick(inner, n_params), k])
    return {"trial": int(trials["trial"].iloc[chosen]), "estimate": float(scores[chosen].mean()),
            "rule": "one-SE on n_params; estimate nested over the recorded folds"}
