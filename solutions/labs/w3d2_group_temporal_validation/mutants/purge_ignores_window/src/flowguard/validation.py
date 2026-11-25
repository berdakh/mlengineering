"""Validation schemes. Each function answers one deployment question; pick by the question.

| function                  | held out                              | estimates performance on            |
|---------------------------|---------------------------------------|-------------------------------------|
| group_kfold_indices       | whole groups                          | a new group from the same population|
| grouped_folds             | the manifest's development folds      | a new experiment (frozen folds)     |
| leave_one_family_out      | every experiment of one family        | a fault mechanism never seen        |
| purged_time_split         | contiguous time blocks, with a buffer | another period of a known series    |
| forward_chaining_split    | a later block, training strictly before | the future of a known series      |

All functions are deterministic. Index-returning functions return sorted integer arrays.
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
    property of row i itself). Two rows share samples iff |i - j| <= window - 1 + horizon.
    """
    if window < 1 or horizon < 0:
        raise ValueError("window must be >= 1 and horizon >= 0")
    return horizon


def group_kfold_indices(groups: Iterable, n_splits: int, seed: int = 0) -> list[tuple[np.ndarray, np.ndarray]]:
    """K folds over rows in which every group is validated exactly once and never split."""
    groups = np.asarray(list(groups))
    unique = np.unique(groups)
    if not 2 <= n_splits <= len(unique):
        raise ValueError(f"n_splits must be between 2 and the number of groups ({len(unique)})")
    shuffled = unique[np.random.default_rng(seed).permutation(len(unique))]
    folds = []
    for k in range(n_splits):
        held_out = np.isin(groups, shuffled[k::n_splits])
        folds.append((np.flatnonzero(~held_out), np.flatnonzero(held_out)))
    return folds


def grouped_folds(manifest: dict) -> list[tuple[list[str], list[str]]]:
    """(train_ids, val_ids) per development fold of the manifest. Test and reference never appear."""
    folds = [list(f) for f in manifest["dev_folds"]]
    fold_of = {e: i for i, fold in enumerate(folds) for e in fold}
    if sum(len(f) for f in folds) != len(fold_of):
        raise ValueError("an experiment appears in more than one development fold")
    forbidden = set(manifest.get("test", [])) | set(manifest.get("reference_normal", []))
    if forbidden & set(fold_of):
        raise ValueError(f"development folds contain test/reference experiments: {sorted(forbidden & set(fold_of))}")
    for group in manifest.get("overlap_groups", []):
        if len({fold_of[e] for e in group if e in fold_of}) > 1:
            raise ValueError(f"overlap group {sorted(group)} is separated across development folds")
    return [(sorted(e for j, f in enumerate(folds) if j != i for e in f), sorted(fold))
            for i, fold in enumerate(folds)]


def leave_one_family_out(tidy: pd.DataFrame, keep_together: Iterable[Iterable[str]] | None = None,
                         ) -> list[tuple[str, list[str], list[str]]]:
    """(family, train_ids, val_ids) for each labelled family present in ``tidy``.

    Training never contains an experiment of the held-out family, nor an experiment that shares an
    overlap group with a held-out experiment (such experiments are dropped, not moved).
    """
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    experiments = experiments[experiments["family"] != REFERENCE_FAMILY]
    groups = [set(g) for g in (keep_together or [])]
    out = []
    for family in sorted(experiments["family"].unique()):
        val = sorted(experiments.loc[experiments["family"] == family, "experiment_id"])
        tainted = set().union(*[g for g in groups if g & set(val)]) if groups else set()
        train = sorted(e for e in experiments["experiment_id"] if e not in val and e not in tainted)
        out.append((family, train, val))
    return out


def _blocks(n: int, n_splits: int) -> list[np.ndarray]:
    if n_splits < 2 or n_splits > n:
        raise ValueError("need 2 <= n_splits <= n")
    return np.array_split(np.arange(n), n_splits)


def purged_time_split(n: int, n_splits: int, purge: int = 0, embargo: int = 0,
                      ) -> list[tuple[np.ndarray, np.ndarray]]:
    """Blocked K-fold over ``n`` time-ordered rows with a buffer around each test block.

    Test blocks are contiguous and partition range(n) in time order. Training is every other row
    except the ``purge`` rows immediately before the block and the ``embargo`` rows immediately
    after it. Training rows may lie after the test block: this estimates performance on another
    period of the same series, not on its future (use forward_chaining_split for that).
    """
    if purge < 0 or embargo < 0:
        raise ValueError("purge and embargo must be >= 0")
    index = np.arange(n)
    folds = []
    for block in _blocks(n, n_splits):
        start, stop = block[0], block[-1]
        keep = (index < start - purge) | (index > stop + embargo)
        folds.append((index[keep], block))
    return folds


def forward_chaining_split(n: int, n_splits: int, gap: int = 0) -> list[tuple[np.ndarray, np.ndarray]]:
    """Expanding-origin splits: the series is cut into ``n_splits + 1`` contiguous blocks; fold k
    trains on everything that ends at least ``gap`` rows before block k + 1 and tests on that block."""
    if gap < 0:
        raise ValueError("gap must be >= 0")
    blocks = _blocks(n, n_splits + 1)
    folds = []
    for block in blocks[1:]:
        train = np.arange(0, max(block[0] - gap, 0))
        if len(train) == 0:
            raise ValueError("gap leaves no training rows for the first fold")
        folds.append((train, block))
    return folds


def rows_for(tidy: pd.DataFrame, experiment_ids: Iterable[str]) -> np.ndarray:
    """Boolean mask of the rows of ``tidy`` that belong to the given experiments."""
    return tidy["experiment_id"].isin(list(experiment_ids)).to_numpy()
