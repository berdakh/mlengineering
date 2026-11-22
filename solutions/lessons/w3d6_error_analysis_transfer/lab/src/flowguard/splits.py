"""Experiment-level split manifest, version v2. SNAPSHOT (docs/FLOWGUARD_SPEC.md, amendments).

v2 supersedes the v1 manifest of w2d4: experiments that share identical rows ("overlap groups")
are kept on the same side of the split. Given to you in this lab; you do not need to edit it.
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
    dup = tidy[tidy.duplicated(key, keep=False)]
    parent: dict[str, str] = {}

    def find(a: str) -> str:
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for _, ids in dup.groupby(key, sort=False)["experiment_id"]:
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

    The unit is the experiment, or the overlap group when ``keep_together`` is given. A labelled
    experiment that shares rows with the fault-free reference is forced into development, so that
    nothing fitted on the reference has seen test rows.
    """
    rng = np.random.default_rng(seed)
    keep_together = [set(g) for g in (keep_together or [])]
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    reference = sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"])
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    tied_to_reference = {e for g in keep_together if g & set(reference) for e in g} - set(reference)
    test: list[str] = []
    dev_units: list[list[str]] = []
    for _, group in labelled.groupby("family", sort=True):
        ids = sorted(group["experiment_id"])
        units, used = [], set()
        for e in ids:
            if e in used:
                continue
            members = next((sorted(g & set(ids)) for g in keep_together if e in g), [e])
            units.append(members)
            used.update(members)
        units = [units[i] for i in rng.permutation(len(units))]
        n_test = max(1, round(test_fraction * len(ids)))
        family_test: list[str] = []
        for unit in units:
            fits = len(family_test) + len(unit) <= n_test
            if fits and not set(unit) & tied_to_reference:
                family_test += unit
            else:
                dev_units.append(unit)
        test += family_test
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for unit in sorted(dev_units, key=len, reverse=True):
        min(folds, key=len).extend(unit)
    return {
        "version": "v2", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": reference,
        "overlap_groups": [sorted(g) for g in keep_together],
        "protocol_b": {"holdout_family": "other"},
    }


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError on overlap, unknown ids, or an overlap group that straddles test and dev."""
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
    for i, fold in enumerate(manifest["dev_folds"]):
        for e in fold:
            seen[e] = f"dev{i}"
    for group in manifest.get("overlap_groups", []):
        where = {"test" if seen.get(e) == "test" else "not-test" for e in group if e in seen}
        if len(where) > 1:
            raise ValueError(f"overlap group {sorted(group)} is split between test and development")
        folds = {seen[e] for e in group if seen.get(e, "").startswith("dev")}
        if len(folds) > 1:
            raise ValueError(f"overlap group {sorted(group)} is split across development folds")


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
