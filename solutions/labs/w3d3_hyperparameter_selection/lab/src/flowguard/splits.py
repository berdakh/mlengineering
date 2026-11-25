"""Experiment-level split manifest, version v2. SNAPSHOT of the w2d4/w3d1 module (docs/maintainers/flowguard-spec.md).

Given to you in this lab; you do not need to edit it. v2 supersedes v1: experiments that share
identical rows ("overlap groups") are kept on the same side of every split, and a labelled
experiment that shares rows with a reference recording is forced into development.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

REFERENCE_FAMILY = "anomaly-free"


def find_overlap_groups(tidy: pd.DataFrame) -> list[set[str]]:
    """Connected components of experiments that share at least one identical (datetime, sensors) row."""
    keys = pd.util.hash_pandas_object(tidy[["datetime", *SENSOR_COLUMNS]], index=False)
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    pairs = pd.DataFrame({"key": keys.to_numpy(), "experiment_id": tidy["experiment_id"].to_numpy()}).drop_duplicates()
    for _, ids in pairs.groupby("key")["experiment_id"]:
        ids = list(ids)
        for other in ids[1:]:
            parent[find(other)] = find(ids[0])
    groups: dict[str, set[str]] = {}
    for e in parent:
        groups.setdefault(find(e), set()).add(e)
    return sorted((g for g in groups.values() if len(g) > 1), key=lambda g: sorted(g))


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25,
                keep_together: list[set[str]] | None = None) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit of assignment is the experiment, or the overlap group when ``keep_together`` is given.
    """
    rng = np.random.default_rng(seed)
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    family_of = dict(zip(experiments["experiment_id"], experiments["family"]))
    reference = sorted(e for e, f in family_of.items() if f == REFERENCE_FAMILY)
    keep_together = [set(g) for g in (keep_together or [])]
    unit_of: dict[str, tuple[str, ...]] = {}
    forced_dev: set[tuple[str, ...]] = set()
    for group in keep_together:
        labelled = tuple(sorted(e for e in group if family_of[e] != REFERENCE_FAMILY))
        for e in labelled:
            unit_of[e] = labelled
        if labelled and any(family_of[e] == REFERENCE_FAMILY for e in group):
            forced_dev.add(labelled)
    test: list[str] = []
    dev_units: list[tuple[str, ...]] = []
    labelled_ids = sorted(e for e, f in family_of.items() if f != REFERENCE_FAMILY)
    for family in sorted({family_of[e] for e in labelled_ids}):
        units = sorted({unit_of.get(e, (e,)) for e in labelled_ids if family_of[e] == family})
        units = [units[i] for i in rng.permutation(len(units))]
        n_target = max(1, round(test_fraction * sum(len(u) for u in units)))
        n_test = 0
        for unit in units:
            if unit not in forced_dev and n_test + len(unit) <= n_target:
                test += unit
                n_test += len(unit)
            else:
                dev_units.append(unit)
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for unit in sorted(dev_units, key=len, reverse=True):       # largest units first, into the emptiest fold
        min(folds, key=len).extend(unit)
    return {
        "version": "v2", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": reference,
        "overlap_groups": [sorted(g) for g in keep_together],
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError on overlap between sides, unknown ids, or a separated overlap group."""
    dev = [e for fold in manifest["dev_folds"] for e in fold]
    sides = {"test": manifest["test"], "dev": dev, "reference_normal": manifest["reference_normal"]}
    seen: dict[str, str] = {}
    known = set(tidy["experiment_id"].unique())
    for name, ids in sides.items():
        for e in ids:
            if e not in known:
                raise ValueError(f"split '{name}' contains unknown experiment {e!r}")
            if e in seen:
                raise ValueError(f"experiment {e!r} is in both '{seen[e]}' and '{name}'")
            seen[e] = name
    fold_of = {e: i for i, fold in enumerate(manifest["dev_folds"]) for e in fold}
    for group in manifest.get("overlap_groups", []):
        labelled = [e for e in group if seen.get(e) != "reference_normal"]
        if len({seen.get(e) for e in labelled}) > 1 or len({fold_of.get(e) for e in labelled}) > 1:
            raise ValueError(f"overlap group {sorted(group)} is separated by the split")
        if len(labelled) < len(group) and any(seen.get(e) == "test" for e in labelled):
            raise ValueError(f"{sorted(group)} shares rows with a reference recording and is in test")


def dev_experiments(manifest: dict) -> list[str]:
    return sorted(e for fold in manifest["dev_folds"] for e in fold)


def save_splits(manifest: dict, path: str | Path, overwrite: bool = False) -> None:
    path = Path(path)
    if path.exists() and not overwrite:
        raise FileExistsError(f"{path} exists; a frozen manifest is not overwritten silently")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n")


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
