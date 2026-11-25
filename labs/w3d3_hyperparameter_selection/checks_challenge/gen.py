"""SYNTHETIC generator of recorded-trial tables for the w3d3 challenge. Used by the checks and to
build the shipped ``challenge/trials.csv``. It models nothing real: a trial has a true score, every
fold adds a shared fold effect and a trial-specific error, and complex trials are noisier.

    python labs/w3d3_hyperparameter_selection/checks_challenge/gen.py   # rewrites the shipped files
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd

N_TRIALS, N_FOLDS = 60, 5
FAMILIES = ("linear", "boosted", "neural")


def make_table(seed: int) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """Returns (trials table, true score per trial, finite-sample test score per trial)."""
    rng = np.random.default_rng(seed)
    family = rng.integers(0, 3, N_TRIALS)
    complexity = np.round(10 ** (2.0 + family + rng.uniform(0, 1, N_TRIALS))).astype(int)   # parameter count
    truth = 0.70 + 0.012 * rng.standard_normal(N_TRIALS)
    noise_sd = 0.015 + 0.012 * family                              # complex families: noisier estimates
    fold_effect = 0.02 * rng.standard_normal(N_FOLDS)
    folds = truth[:, None] + fold_effect[None, :] + noise_sd[:, None] * rng.standard_normal((N_TRIALS, N_FOLDS))
    test = truth + 0.012 * rng.standard_normal(N_TRIALS)
    table = pd.DataFrame({"trial": np.arange(N_TRIALS), "family": [FAMILIES[f] for f in family],
                          "n_params": complexity,
                          "learning_rate": np.round(10 ** rng.uniform(-4, -1, N_TRIALS), 6)})
    for k in range(N_FOLDS):
        table[f"fold_{k}"] = np.round(folds[:, k], 4)
    return table, truth, test


def write_shipped(seed: int = 2026) -> None:
    here = Path(__file__).resolve().parents[1] / "challenge"
    table, _, test = make_table(seed)
    table.to_csv(here / "trials.csv", index=False, lineterminator="\n")
    sealed = base64.b64encode(json.dumps([round(float(t), 4) for t in test]).encode()).decode()
    (here / "sealed_test_scores.b64").write_text(sealed + "\n")
    print(f"wrote {here / 'trials.csv'} and sealed_test_scores.b64 (seed {seed})")


if __name__ == "__main__":
    write_shipped()
