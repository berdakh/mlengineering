"""Experiment-level split manifest, version v2. SNAPSHOT (docs/FLOWGUARD_SPEC.md, amendments).

Given to you in this lab; you do not need to edit it. The authoritative v2 module is the one you
write in w3d1; this snapshot implements the same contract so the lab runs on its own.

v2 adds overlap groups: SKAB files that share identical rows are kept on one side of every split.
A labelled experiment that shares rows with the fault-free reference recording is placed in the
development set, never in the test set.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from flowguard.data import SENSOR_COLUMNS

REFERENCE_FAMILY = "anomaly-free"


def find_overlap_groups(tidy: pd.DataFrame) -> list[set[str]]:
    """Connected components of experiments that share at least one identical row
    (same timestamp and same eight sensor values)."""
    key = ["datetime", *SENSOR_COLUMNS]
    shared = tidy[tidy.duplicated(key, keep=False)]
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for _, ids in shared.groupby(key, sort=False)["experiment_id"]:
        ids = sorted(set(ids))
        for other in ids[1:]:
            parent[find(other)] = find(ids[0])
    groups: dict[str, set[str]] = {}
    for e in parent:
        groups.setdefault(find(e), set()).add(e)
    return sorted((g for g in groups.values() if len(g) > 1), key=lambda g: sorted(g))


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25,
                keep_together: list[set[str]] | None = None) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit of assignment is the overlap group (a single experiment when it overlaps nothing).
    Each family contributes about ``test_fraction`` of its experiments to the test set.
    """
    rng = np.random.default_rng(seed)
    keep_together = [set(g) for g in (find_overlap_groups(tidy) if keep_together is None else keep_together)]
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    reference = sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"])
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    group_of = {e: frozenset(g) for g in keep_together for e in g}
    test: list[str] = []
    dev_units: list[list[str]] = []
    for _, fam in labelled.groupby("family", sort=True):
        ids = set(fam["experiment_id"])
        units = sorted({tuple(sorted(group_of.get(e, frozenset([e])) & ids)) for e in ids})
        units = [units[i] for i in rng.permutation(len(units))]
        n_test = max(1, round(test_fraction * len(ids)))
        for unit in units:
            touches_reference = any(r in group_of.get(unit[0], ()) for r in reference)
            already = sum(e in ids for e in test)
            if not touches_reference and already + len(unit) <= n_test:
                test += unit
            else:
                dev_units.append(list(unit))
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for unit in sorted(dev_units, key=len, reverse=True):          # largest units first, into the emptiest fold
        min(folds, key=len).extend(unit)
    return {
        "version": "v2", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": reference,
        "overlap_groups": [sorted(g) for g in keep_together],
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if an experiment is on two sides, is unknown, or an overlap group is separated."""
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
        in_test = [e for e in group if seen.get(e) == "test"]
        if in_test and len(in_test) != len(group):
            raise ValueError(f"overlap group {sorted(group)} is separated by the test split")
        if len({fold_of[e] for e in group if e in fold_of}) > 1:
            raise ValueError(f"overlap group {sorted(group)} is spread over several dev folds")


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
