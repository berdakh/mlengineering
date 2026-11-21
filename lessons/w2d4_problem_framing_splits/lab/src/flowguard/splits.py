"""Versioned split definitions - STARTER. Implement the four functions (lesson section 4).

Contract (docs/FLOWGUARD_SPEC.md):

    make_splits(tidy, seed=0, n_folds=4, test_fraction=0.25) -> dict
    validate_splits(manifest, tidy) -> None      # raises ValueError on any leak
    save_splits(manifest, path, overwrite=False) -> Path   # FileExistsError if frozen
    load_splits(path) -> dict

Manifest:
    {"version": "v1", "seed": 0, "unit": "experiment_id", "test": [...], "dev_folds": [[...], ...],
     "reference_normal": ["anomaly-free/anomaly-free"], "protocol_b": {"holdout_family": "other"}}
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25) -> dict:
    raise NotImplementedError("Task 2")


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    raise NotImplementedError("Task 3")


def save_splits(manifest: dict, path: str | Path, overwrite: bool = False) -> Path:
    raise NotImplementedError("Task 4")


def load_splits(path: str | Path) -> dict:
    raise NotImplementedError("Task 4")
