"""Experiment-level split manifest, v2. SNAPSHOT (docs/maintainers/flowguard-spec.md, "Amendments after Week 2").

Given to you in this lab; you do not need to edit it. v2 differs from the w2d4 manifest in one way:
experiments that share identical rows (``keep_together`` groups) always land on the same side.
It supersedes ``splits/v1.json``; w3d1 is where the project's own v2 manifest is produced.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

REFERENCE_FAMILY = "anomaly-free"

# Connected components of "these two files contain identical rows" on SKAB v0.9 (docs/guides/project.md).
SKAB_OVERLAP_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"anomaly-free/anomaly-free", "other/5"}),
    frozenset({"other/12", "other/13"}),
    frozenset({"other/2", "other/3", "other/4"}),
    frozenset({"other/10", "other/11"}),
)


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25,
                keep_together=None) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit is the experiment, or the whole ``keep_together`` group it belongs to. Within each
    family, units are shuffled and moved to the test set until it holds at least
    ``round(test_fraction * n)`` experiments (at least 1); the rest are dealt into the dev folds
    unit by unit, so a group is never divided between folds either.
    """
    rng = np.random.default_rng(seed)
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    labelled_ids = set(labelled["experiment_id"])
    groups = [sorted(set(g) & labelled_ids) for g in (keep_together or [])]
    groups = [g for g in groups if len(g) > 1]
    grouped = {e: i for i, g in enumerate(groups) for e in g}
    test: list[str] = []
    dev_units: list[list[str]] = []
    for _, fam in labelled.groupby("family", sort=True):
        ids = sorted(fam["experiment_id"])
        units, seen = [], set()
        for e in ids:
            if e in seen:
                continue
            unit = [x for x in groups[grouped[e]] if x in ids] if e in grouped else [e]
            seen.update(unit)
            units.append(unit)
        units = [units[i] for i in rng.permutation(len(units))]
        n_test = max(1, round(test_fraction * len(ids)))
        taken = 0
        for unit in units:
            if taken < n_test:
                test += unit
                taken += len(unit)
            else:
                dev_units.append(unit)
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for unit in sorted(dev_units, key=len, reverse=True):       # largest units first, into the emptiest fold
        min(folds, key=len).extend(unit)
    return {
        "version": "v2", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"]),
        "overlap_groups": [sorted(g) for g in (keep_together or [])],
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if an experiment is on two sides, is unknown, or an overlap group is divided.

    The fault-free reference is exempt from the group rule: it is never evaluated, and no detector
    in this lab is fitted on it.
    """
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
    fold_of = {e: f"dev fold {i}" for i, fold in enumerate(manifest["dev_folds"]) for e in fold}
    fold_of.update({e: "test" for e in manifest["test"]})
    for group in manifest.get("overlap_groups", []):
        placed = {fold_of[e] for e in group if e in fold_of}
        if len(placed) > 1:
            raise ValueError(f"overlap group {sorted(group)} is divided between {sorted(placed)}")


def dev_experiments(manifest: dict) -> list[str]:
    return sorted(e for fold in manifest["dev_folds"] for e in fold)


def save_splits(manifest: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(manifest, indent=2) + "\n")


def load_splits(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())
