"""Versioned split definitions. The unit of splitting is the experiment, never the row.

A split is a *decision*, so it is stored as data (a JSON manifest under version control),
not recomputed from a seed each time. ``make_splits`` is run once; everything afterwards
reads the manifest and ``validate_splits`` guards it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

VERSION = "v1"
UNIT = "experiment_id"
NORMAL_FAMILY = "anomaly-free"
HOLDOUT_FAMILY = "other"


def _experiments_by_family(tidy: pd.DataFrame) -> dict[str, list[str]]:
    """family -> sorted experiment ids. Sorting removes any dependence on row order."""
    pairs = tidy[[UNIT, "family"]].drop_duplicates()
    if pairs[UNIT].duplicated().any():
        raise ValueError("an experiment_id appears under more than one family")
    return {fam: sorted(g[UNIT]) for fam, g in pairs.groupby("family", sort=True)}


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25) -> dict:
    """Assign every labelled experiment to the fixed test set or to exactly one dev fold.

    Stratified by family: each family with at least two experiments contributes at least
    one experiment to the test set and keeps at least one for development. The fault-free
    recording is never evaluated on; it is listed as reference-normal data.
    """
    if not 0.0 < test_fraction < 1.0:
        raise ValueError("test_fraction must be in (0, 1)")
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    rng = np.random.default_rng(seed)
    by_family = _experiments_by_family(tidy)
    test: list[str] = []
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    next_fold = 0
    for family, ids in by_family.items():
        if family == NORMAL_FAMILY:
            continue
        shuffled = [ids[i] for i in rng.permutation(len(ids))]
        n_test = 0 if len(ids) < 2 else min(len(ids) - 1, max(1, round(test_fraction * len(ids))))
        test.extend(shuffled[:n_test])
        for exp in shuffled[n_test:]:           # round-robin keeps folds balanced within family
            folds[next_fold % n_folds].append(exp)
            next_fold += 1
    return {
        "version": VERSION,
        "seed": int(seed),
        "unit": UNIT,
        "test": sorted(test),
        "dev_folds": [sorted(f) for f in folds],
        "reference_normal": list(by_family.get(NORMAL_FAMILY, [])),
        "protocol_b": {"holdout_family": HOLDOUT_FAMILY},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if the test set and the dev folds share an experiment."""
    dev = {e for fold in manifest["dev_folds"] for e in fold}
    shared = sorted(set(manifest["test"]) & dev)
    if shared:
        raise ValueError(f"experiments in both test and dev: {shared}")


def save_splits(manifest: dict, path: str | Path, overwrite: bool = False) -> Path:
    """Write the manifest as stable, diff-friendly JSON. Refuses to replace a frozen split."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; a split is frozen once written (use a new version)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def rows_for(tidy: pd.DataFrame, experiment_ids: list[str]) -> pd.DataFrame:
    """All rows of the given experiments (the only sanctioned way to slice by split)."""
    return tidy[tidy[UNIT].isin(experiment_ids)]
