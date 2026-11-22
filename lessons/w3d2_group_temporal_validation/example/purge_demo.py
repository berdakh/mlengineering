"""Worked example, part 2 (SYNTHETIC): overlapping windows across a split boundary.

    python lessons/w3d2_group_temporal_validation/example/purge_demo.py

Row i has
    features(i) = trailing means over W rows of three slow "context" series (think ambient
                  temperature, supply voltage, load) that are INDEPENDENT of the target series x
    label(i)    = 1 if the mean of x over the next H rows (i+1 .. i+H) is positive, x white noise
The features carry no information about the label, so the true ROC-AUC is exactly 0.5.
But rows close in time have nearly identical features (overlapping feature windows) AND nearly
identical labels (overlapping label windows). A model that can match a validation row to its
temporal neighbours in the training set copies their labels. Any value above 0.5 is leakage.
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import KFold
from sklearn.neighbors import KNeighborsClassifier

N, W, H = 6000, 40, 30


def build(seed: int):
    rng = np.random.default_rng(seed)
    idx = np.arange(W, W + N)

    def trailing_mean(series: np.ndarray, w: int) -> np.ndarray:
        c = np.concatenate([[0.0], np.cumsum(series)])
        return (c[idx + 1] - c[idx + 1 - w]) / w

    context = rng.standard_normal((3, N + W + H))
    X = np.column_stack([trailing_mean(s, W) for s in context])
    c = np.concatenate([[0.0], np.cumsum(rng.standard_normal(N + W + H))])
    y = ((c[idx + 1 + H] - c[idx + 1]) > 0).astype(int)
    return X, y


def blocked(n: int, n_splits: int, purge: int, embargo: int):
    index = np.arange(n)
    for block in np.array_split(index, n_splits):
        keep = (index < block[0] - purge) | (index > block[-1] + embargo)
        yield index[keep], block


def auc(X, y, folds) -> float:
    truth, score = [], []
    for tr, va in folds:
        model = KNeighborsClassifier(n_neighbors=5).fit(X[tr], y[tr])
        truth.append(y[va])
        score.append(model.predict_proba(X[va])[:, 1])
    return roc_auc_score(np.concatenate(truth), np.concatenate(score))


def main() -> None:
    need = W - 1 + H
    schemes = {
        "shuffled 5-fold": lambda n: KFold(5, shuffle=True, random_state=0).split(np.arange(n)),
        "blocked, 5 blocks of 1200 rows, no buffer": lambda n: blocked(n, 5, 0, 0),
        "blocked, 300 blocks of 20 rows, no buffer": lambda n: blocked(n, 300, 0, 0),
        "blocked, 300 blocks, purge = embargo = 10": lambda n: blocked(n, 300, 10, 10),
        f"blocked, 300 blocks, purge = {need}, embargo = 0": lambda n: blocked(n, 300, need, 0),
        f"blocked, 300 blocks, purge = embargo = {H} (label horizon only)": lambda n: blocked(n, 300, H, H),
        f"blocked, 300 blocks, purge = embargo = {need} (W - 1 + H)": lambda n: blocked(n, 300, need, need),
    }
    print(f"true ROC-AUC = 0.500. W = {W}, H = {H}, n = {N}; mean and s.d. over 10 seeds")
    print("| scheme | pooled out-of-fold ROC-AUC |")
    print("|---|---|")
    for name, make in schemes.items():
        values = [auc(*build(seed), make(N)) for seed in range(10)]
        print(f"| {name} | {np.mean(values):.3f} +- {np.std(values):.3f} |")


if __name__ == "__main__":
    main()
