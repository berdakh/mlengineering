"""Validation schemes. Each function answers one deployment question; pick by the question.

| function                  | held out                              | estimates performance on            |
|---------------------------|---------------------------------------|-------------------------------------|
| group_kfold_indices       | whole groups                          | a new group from the same population|
| grouped_folds             | the manifest's development folds      | a new experiment (frozen folds)     |
| leave_one_family_out      | every experiment of one family        | a fault mechanism never seen        |
| purged_time_split         | contiguous time blocks, with a buffer | another period of a known series    |
| forward_chaining_split    | a later block, training strictly before | the future of a known series      |

All functions are deterministic. Index-returning functions return sorted integer NumPy arrays.

YOUR TASK (lesson w3d2, section 4): implement the six functions marked TODO. `rows_for` is given.
You may use scikit-learn splitters inside them or write them by hand; the checks only look at
what the functions return.
"""
from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

REFERENCE_FAMILY = "anomaly-free"


def required_purge(window: int, horizon: int = 0) -> int:
    """Rows to drop on each side of a test block so that no training row shares raw samples with it.

    A row at index i is built from raw samples [i - window + 1, i + horizon]: ``window`` rows of
    feature history ending at i, and a label that looks ``horizon`` rows ahead (0 = the label is a
    property of row i itself). Raise ValueError if window < 1 or horizon < 0.
    """
    raise NotImplementedError("TODO task 1")


def group_kfold_indices(groups: Iterable, n_splits: int, seed: int = 0) -> list[tuple[np.ndarray, np.ndarray]]:
    """K folds over rows in which every group is validated exactly once and never split.

    Returns ``[(train_idx, val_idx), ...]`` of row positions. Which groups share a fold depends on
    ``seed`` (and only on it).
    Raise ValueError unless 2 <= n_splits <= number of distinct groups.
    """
    raise NotImplementedError("TODO task 2")


def grouped_folds(manifest: dict) -> list[tuple[list[str], list[str]]]:
    """(train_ids, val_ids) per development fold of the manifest, in fold order.

    Fold k validates on ``manifest["dev_folds"][k]`` and trains on the other development folds.
    Test and reference experiments never appear. Raise ValueError if the manifest is unsafe to use:
    a test/reference experiment listed in a development fold, or an overlap group
    (``manifest["overlap_groups"]``) whose members sit in different folds. Do not modify ``manifest``.
    """
    raise NotImplementedError("TODO task 3")


def leave_one_family_out(tidy: pd.DataFrame, keep_together: Iterable[Iterable[str]] | None = None,
                         ) -> list[tuple[str, list[str], list[str]]]:
    """(family, train_ids, val_ids) for each labelled family present in ``tidy``.

    ``val_ids`` is every experiment of the family. Training is every other labelled experiment,
    EXCEPT experiments that share an overlap group (``keep_together``) with a held-out experiment:
    those are dropped from training (not moved into validation). The reference family
    ("anomaly-free") appears on neither side.
    """
    raise NotImplementedError("TODO task 4")


def purged_time_split(n: int, n_splits: int, purge: int = 0, embargo: int = 0,
                      ) -> list[tuple[np.ndarray, np.ndarray]]:
    """Blocked K-fold over ``n`` time-ordered rows with a buffer around each test block.

    Test blocks are contiguous, in time order, sizes differing by at most one, and together they
    cover range(n) exactly once. Training is every other row except the ``purge`` rows immediately
    before the block and the ``embargo`` rows immediately after it. No shuffling, ever.
    Raise ValueError for negative buffers or if not 2 <= n_splits <= n.
    """
    raise NotImplementedError("TODO task 5")


def forward_chaining_split(n: int, n_splits: int, gap: int = 0) -> list[tuple[np.ndarray, np.ndarray]]:
    """Expanding-origin splits: cut range(n) into ``n_splits + 1`` contiguous blocks (sizes differing
    by at most one); fold k tests on block k + 1 and trains on rows 0 .. (start of that block - gap - 1).

    Raise ValueError if gap < 0 or if the gap leaves a fold with no training rows.
    """
    raise NotImplementedError("TODO task 6")


def rows_for(tidy: pd.DataFrame, experiment_ids: Iterable[str]) -> np.ndarray:
    """Boolean mask of the rows of ``tidy`` that belong to the given experiments. (Given.)"""
    return tidy["experiment_id"].isin(list(experiment_ids)).to_numpy()
