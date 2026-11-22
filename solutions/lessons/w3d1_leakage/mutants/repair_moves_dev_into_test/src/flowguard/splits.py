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
    row_hash = pd.util.hash_pandas_object(tidy[_ROW_KEY], index=False)
    pairs = pd.DataFrame({"h": row_hash.to_numpy(), "e": tidy["experiment_id"].to_numpy()}).drop_duplicates()
    shared = pairs[pairs.duplicated("h", keep=False)]
    counts: dict[tuple[str, str], int] = {}
    for _, members in shared.groupby("h")["e"]:
        ids = sorted(members)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                counts[(a, b)] = counts.get((a, b), 0) + 1

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), n in counts.items():
        if n >= min_shared_rows:
            parent[find(a)] = find(b)
    groups: dict[str, set[str]] = {}
    for x in parent:
        groups.setdefault(find(x), set()).add(x)
    return sorted((g for g in groups.values() if len(g) > 1), key=min)


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

    The unit is the experiment. With ``keep_together`` (an iterable of sets of experiment ids, e.g.
    the output of ``find_overlap_groups``) the unit becomes the *group*: all members go to the test
    set or to one single development fold. A group that contains a reference-normal recording is
    never placed in the test set, because detectors are fitted on the reference recording.
    Without ``keep_together`` the result is the v1 manifest, unchanged.
    """
    rng = np.random.default_rng(seed)
    experiments = tidy[["experiment_id", "family"]].drop_duplicates()
    reference = sorted(experiments.loc[experiments["family"] == REFERENCE_FAMILY, "experiment_id"])
    labelled = experiments[experiments["family"] != REFERENCE_FAMILY]
    groups = _merge_groups(keep_together)
    group_of = {e: i for i, g in enumerate(groups) for e in g}
    touches_reference = {i for i, g in enumerate(groups) if g & set(reference)}

    test: list[str] = []
    dev_units: list[list[str]] = []
    for _, fam in labelled.groupby("family", sort=True):
        ids = sorted(fam["experiment_id"])
        units: dict[object, list[str]] = {}
        for e in ids:                                   # a unit = one group, or one lone experiment
            units.setdefault(("g", group_of[e]) if e in group_of else ("e", e), []).append(e)
        ordered = list(units.items())
        ordered = [ordered[i] for i in rng.permutation(len(ordered))]
        n_test = max(1, round(test_fraction * len(ids)))
        taken = 0
        for key, members in ordered:
            dev_only = key[0] == "g" and key[1] in touches_reference
            if not dev_only and taken + len(members) <= n_test:
                test += members
                taken += len(members)
            else:
                dev_units.append(members)
    folds: list[list[str]] = [[] for _ in range(n_folds)]
    for members in dev_units:                           # whole unit into the currently smallest fold
        min(folds, key=len).extend(members)
    manifest = {
        "version": "v2" if keep_together is not None else "v1", "seed": seed, "unit": "experiment_id",
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "reference_normal": reference,
        "protocol_b": {"holdout_family": "other"},
    }
    if keep_together is not None:
        manifest["overlap_groups"] = [sorted(g) for g in sorted(groups, key=min)]
    return manifest


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
    groups = _merge_groups(keep_together)
    test = list(manifest["test"])
    folds = [list(f) for f in manifest["dev_folds"]]
    reference = set(manifest["reference_normal"])
    for group in sorted(groups, key=min):
        members = sorted(group - reference)
        in_test = [e for e in members if e in test]
        fold_counts = [sum(e in fold for e in members) for fold in folds]
        must_leave_test = bool(group & reference) and in_test
        if not must_leave_test and (sum(c > 0 for c in fold_counts) + bool(in_test)) <= 1:
            continue
        to_test = bool(in_test) and not must_leave_test
        home = int(np.argmax(fold_counts)) if any(fold_counts) else int(np.argmin([len(f) for f in folds]))
        for e in members:
            if e in test:
                test.remove(e)
            for fold in folds:
                if e in fold:
                    fold.remove(e)
            (test if to_test else folds[home]).append(e)
    repaired = dict(manifest)
    repaired.update({
        "version": "v2", "repaired_from": manifest.get("version", "v1"),
        "test": sorted(test), "dev_folds": [sorted(f) for f in folds],
        "overlap_groups": [sorted(g) for g in sorted(groups, key=min)],
    })
    return repaired


def _side_of(manifest: dict) -> dict[str, str]:
    side = {e: "test" for e in manifest["test"]}
    for i, fold in enumerate(manifest["dev_folds"]):
        side.update({e: f"dev fold {i}" for e in fold})
    side.update({e: "reference_normal" for e in manifest["reference_normal"]})
    return side


def validate_splits(manifest: dict, tidy: pd.DataFrame) -> None:
    """Raise ValueError unless the manifest is a leak-free assignment of the experiments in ``tidy``.

    Checked: every id is known and appears once; no two experiments that share rows are on
    different sides (test / a dev fold); nothing that shares rows with a reference-normal
    recording is in the test set. The overlap groups are recomputed from ``tidy``, so a v1
    manifest written before the duplicates were known is rejected too.
    """
    dev = [e for fold in manifest["dev_folds"] for e in fold]
    named = {"test": manifest["test"], "dev": dev, "reference_normal": manifest["reference_normal"]}
    seen: dict[str, str] = {}
    known = set(tidy["experiment_id"].unique())
    for name, ids in named.items():
        for e in ids:
            if e not in known:
                raise ValueError(f"split '{name}' contains unknown experiment {e!r}")
            if e in seen:
                raise ValueError(f"experiment {e!r} is in both '{seen[e]}' and '{name}'")
            seen[e] = name
    side = _side_of(manifest)
    groups = _merge_groups([*find_overlap_groups(tidy), *manifest.get("overlap_groups", [])])
    for group in groups:
        sides = {side[e] for e in group if e in side}
        if "reference_normal" in sides and "test" in sides:
            raise ValueError(f"experiments {sorted(group)} share rows with a reference-normal recording "
                             "but one of them is in the test set")
        evaluated = sides - {"reference_normal"}
        if len(evaluated) > 1:
            raise ValueError(f"experiments {sorted(group)} share rows but are separated: {sorted(evaluated)}")


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
