"""Experiment-level split manifest, version 2: experiments that share rows stay together.

v1 (w2d4) treated every file as an independent experiment. On the real data five pairs of files
contain identical rows, so v1 can put the same measurements on both sides of a split.
v2 adds ``find_overlap_groups``, the ``keep_together`` constraint for new splits, ``repair_splits``
for a split that is already in use, and a ``validate_splits`` that refuses any manifest that separates experiments sharing rows.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

REFERENCE_FAMILY = "anomaly-free"
_ROW_KEY = ["datetime", *SENSOR_COLUMNS]


def find_overlap_groups(tidy: pd.DataFrame, min_shared_rows: int = 1) -> list[set[str]]:
    """Groups of experiments connected by shared rows (same timestamp and same eight sensor values).

    Two experiments are linked when they share at least ``min_shared_rows`` identical rows; groups
    are the connected components of that graph with two or more members. Labels are ignored on
    purpose: the same measurements with different labels are still the same measurements.
    The result is ordered by each group's smallest id, so it is deterministic.
    """
    raise NotImplementedError("w3d1 lab: implement find_overlap_groups")


def _merge_groups(groups) -> list[set[str]]:
    """Union groups that share a member, so ``keep_together`` may be given in any form."""
    merged: list[set[str]] = []
    for group in (set(g) for g in groups or []):
        for other in [m for m in merged if m & group]:
            group |= other
            merged.remove(other)
        merged.append(group)
    return merged


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25,
                keep_together=None) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit is the experiment. Each family contributes ``round(test_fraction * n)`` (at least 1)
    experiments to the test set, so every family is present on both sides.
    """
    if keep_together is not None:
        raise NotImplementedError("w3d1 lab: honour keep_together (groups stay on one side; see the lesson)")
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


def repair_splits(manifest: dict, keep_together) -> dict:
    """Smallest change to an existing manifest that keeps every group together (returns a new v2 dict).

    A split that has already been used should not be re-drawn: re-drawing moves development
    experiments, which were used for tuning, into the test set. The repair only ever moves
    experiments OUT of the test set or between development folds:

    * a separated group goes to the development fold that already holds most of its members
      (ties: the lowest fold index); test members follow it there;
    * a group that contains a reference-normal recording is moved out of the test set;
    * a group that lies entirely in the test set is left alone.
    """
    raise NotImplementedError("w3d1 lab: implement repair_splits")


def _side_of(manifest: dict) -> dict[str, str]:
    side = {e: "test" for e in manifest["test"]}
    for i, fold in enumerate(manifest["dev_folds"]):
        side.update({e: f"dev fold {i}" for e in fold})
    side.update({e: "reference_normal" for e in manifest["reference_normal"]})
    return side


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
    # TODO (w3d1): also reject manifests that separate experiments sharing rows, and manifests that
    # put anything sharing rows with a reference-normal recording into the test set.


def dev_experiments(manifest: dict) -> list[str]:
    return sorted(e for fold in manifest["dev_folds"] for e in fold)


def diff_manifests(old: dict, new: dict) -> dict[str, tuple[str, str]]:
    """Experiments whose side changed between two manifests: id -> (old side, new side)."""
    a, b = _side_of(old), _side_of(new)
    return {e: (a.get(e, "absent"), b.get(e, "absent")) for e in sorted(set(a) | set(b)) if a.get(e) != b.get(e)}


def save_splits(manifest: dict, path: str | Path, overwrite: bool = False) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} already exists; a split is frozen once written (use a new version)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
