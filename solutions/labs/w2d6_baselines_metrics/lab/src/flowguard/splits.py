"""Experiment-level split manifest. SNAPSHOT of the w2d4 module (docs/maintainers/flowguard-spec.md).

Given to you in this lab; you do not need to edit it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE_FAMILY = "anomaly-free"


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit is the experiment. Each family contributes ``round(test_fraction * n)`` (at least 1)
    experiments to the test set, so every family is present on both sides.
    """
    rng = np.random.default_rng(seed)
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    test: list[str] = []
    dev: list[str] = []
    for _, group in labelled.groupby("family", sort=True):
        ids = sorted(group["experiment_id"])
        ids = [ids[i] for i in rng.permutation(len(ids))]
        n_test = max(1, round(test_fraction * len(ids)))
        test += ids[:n_test]
        dev += ids[n_test:]
    folds = [sorted(dev[i::n_folds]) for i in range(n_folds)]
    return {
        "version": "v1", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": folds,
        "reference_normal": sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"]),
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if an experiment is on two sides or is unknown to ``tidy``."""
    dev = [e for fold in manifest["dev_folds"] for e in fold]
    groups = {"test": manifest["test"], "dev": dev, "reference_normal": manifest["reference_normal"]}
    seen: dict[str, str] = {}
    known = set(tidy["experiment_id"].unique())
    for name, ids in groups.items():
        for e in ids:
            if e not in known:
                raise ValueError(f"split '{name}' contains unknown experiment {e!r}")
            if e in seen:
                raise ValueError(f"experiment {e!r} is in both '{seen[e]}' and '{name}'")
            seen[e] = name


def dev_experiments(manifest: dict) -> list[str]:
    return sorted(e for fold in manifest["dev_folds"] for e in fold)


def save_splits(manifest: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(manifest, indent=2) + "\n")


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
