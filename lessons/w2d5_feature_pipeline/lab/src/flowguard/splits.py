"""Versioned split manifests by experiment (snapshot written to docs/FLOWGUARD_SPEC.md; see w2d4)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE_FAMILY = "anomaly-free"


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25) -> dict:
    """Assign whole labelled experiments to test or to one of ``n_folds`` development folds."""
    labelled = tidy.loc[tidy["family"] != REFERENCE_FAMILY, "experiment_id"]
    ids = sorted(labelled.unique())
    order = np.random.default_rng(seed).permutation(len(ids))
    shuffled = [ids[i] for i in order]
    n_test = max(1, round(test_fraction * len(shuffled)))
    test, dev = sorted(shuffled[:n_test]), shuffled[n_test:]
    folds = [sorted(dev[i::n_folds]) for i in range(n_folds)]
    reference = sorted(tidy.loc[tidy["family"] == REFERENCE_FAMILY, "experiment_id"].unique())
    return {"version": "v1", "seed": seed, "unit": "experiment_id", "test": test, "dev_folds": folds,
            "reference_normal": reference, "protocol_b": {"holdout_family": "other"}}


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if an experiment is on two sides or is unknown."""
    groups = [manifest["test"], *manifest["dev_folds"], manifest["reference_normal"]]
    flat = [e for g in groups for e in g]
    if len(flat) != len(set(flat)):
        raise ValueError("an experiment_id appears in more than one split")
    unknown = set(flat) - set(tidy["experiment_id"].unique())
    if unknown:
        raise ValueError(f"split manifest names unknown experiments: {sorted(unknown)}")


def save_splits(manifest: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def training_experiments(manifest: dict, fold: int) -> list[str]:
    """Development experiments NOT in validation fold ``fold`` (never includes test)."""
    return sorted(e for i, f in enumerate(manifest["dev_folds"]) if i != fold for e in f)
