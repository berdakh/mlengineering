"""Experiment-level split manifest, version v2. SNAPSHOT (docs/maintainers/flowguard-spec.md, amendments).

Given to you in this lab; you do not need to edit it. v2 differs from the w2d4 manifest in one way:
experiments that share identical rows ("overlap groups") are kept on the same side of every split.
Lesson w3d1 derives this; here it is supplied so that the validation schemes start from a sound base.
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
    key = ["datetime", *SENSOR_COLUMNS]
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    shared = tidy[tidy.duplicated(key, keep=False)]
    for _, rows in shared.groupby(key, sort=False):
        ids = sorted(set(rows["experiment_id"]))
        for other in ids[1:]:
            parent[find(other)] = find(ids[0])
    groups: dict[str, set[str]] = {}
    for e in parent:
        groups.setdefault(find(e), set()).add(e)
    return sorted((g for g in groups.values() if len(g) > 1), key=lambda g: sorted(g))


def make_splits(tidy: pd.DataFrame, seed: int = 0, n_folds: int = 4, test_fraction: float = 0.25,
                keep_together: list[set[str]] | None = None) -> dict:
    """Split labelled experiments into a test set and ``n_folds`` development folds.

    The unit of assignment is the *block*: an overlap group (restricted to labelled experiments) or
    a single experiment. Per family, blocks are shuffled and assigned to test until the family has
    about ``test_fraction`` of its experiments there; the remaining blocks are dealt to the folds,
    always into the currently smallest fold.
    """
    rng = np.random.default_rng(seed)
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    family_of = dict(zip(labelled["experiment_id"], labelled["family"]))
    groups = [set(g) for g in (keep_together or [])]
    block_of: dict[str, frozenset[str]] = {}
    for e in family_of:
        members = next((g for g in groups if e in g), {e})
        block_of[e] = frozenset(m for m in members if m in family_of)
    test: list[str] = []
    dev_blocks: list[list[str]] = []
    for family in sorted(set(family_of.values())):
        blocks = sorted({b for e, b in block_of.items() if family_of[e] == family}, key=lambda b: sorted(b))
        blocks = [blocks[i] for i in rng.permutation(len(blocks))]
        n_family = sum(1 for f in family_of.values() if f == family)
        n_target = max(1, round(test_fraction * n_family))
        n_in_test = 0
        for block in blocks:
            if n_in_test < n_target and n_in_test + len(block) <= n_target + 1:
                test += sorted(block)
                n_in_test += len(block)
            else:
                dev_blocks.append(sorted(block))
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for block in dev_blocks:
        min(folds, key=len).extend(block)
    return {
        "version": "v2", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"]),
        "overlap_groups": [sorted(g) for g in groups],
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError if an experiment is on two sides, is unknown, or an overlap group is separated.

    The reference recording is exempt from the overlap rule: it is never trained on with labels and
    never evaluated, and the amendments record its overlap with ``other/5`` as a known limitation.
    """
    sides = {"test": manifest["test"], "reference_normal": manifest["reference_normal"]}
    sides.update({f"dev_fold_{i}": fold for i, fold in enumerate(manifest["dev_folds"])})
    seen: dict[str, str] = {}
    known = set(tidy["experiment_id"].unique())
    for name, ids in sides.items():
        for e in ids:
            if e not in known:
                raise ValueError(f"split '{name}' contains unknown experiment {e!r}")
            if e in seen:
                raise ValueError(f"experiment {e!r} is in both '{seen[e]}' and '{name}'")
            seen[e] = name
    for group in manifest.get("overlap_groups", []):
        where = {seen[e] for e in group if e in seen and seen[e] != "reference_normal"}
        if len(where) > 1:
            raise ValueError(f"overlap group {sorted(group)} is separated across {sorted(where)}")


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
