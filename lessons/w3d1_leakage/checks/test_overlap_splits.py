"""Duplicate-aware splitting: find_overlap_groups, make_splits(keep_together=...), repair_splits, validate_splits."""
from __future__ import annotations

import copy

import pytest

from conftest import as_sets, plant_overlap, side_of, synth_tidy

REF = "anomaly-free/anomaly-free"


def overlapping(tidy):
    t = plant_overlap(tidy, "other/1", "other/2", n=6)
    t = plant_overlap(t, "other/2", "other/3", n=4, src_offset=20, dest_offset=20)   # chain 1-2-3
    t = plant_overlap(t, "valve1/0", "valve1/5", n=3, flip_labels=True, src_offset=18, dest_offset=18)
    return plant_overlap(t, REF, "other/5", n=8)


EXPECTED = [frozenset({REF, "other/5"}), frozenset({"other/1", "other/2", "other/3"}),
            frozenset({"valve1/0", "valve1/5"})]


def test_no_groups_on_clean_data(splits, tidy):
    assert list(splits.find_overlap_groups(tidy)) == []


def test_groups_are_connected_components(splits, tidy):
    assert as_sets(splits.find_overlap_groups(overlapping(tidy))) == sorted(EXPECTED, key=min)


def test_shared_rows_with_contradictory_labels_still_count(splits, tidy):
    t = plant_overlap(tidy, "valve2/0", "valve2/1", n=5, flip_labels=True, src_offset=17, dest_offset=17)
    assert as_sets(splits.find_overlap_groups(t)) == [frozenset({"valve2/0", "valve2/1"})]


def test_same_sensor_values_at_other_times_are_not_overlap(splits, tidy):
    t = tidy.copy()
    a = t.index[t["experiment_id"] == "valve1/1"][:5]
    b = t.index[t["experiment_id"] == "valve1/2"][:5]
    sensors = [c for c in t.columns if c not in ("experiment_id", "family", "t", "datetime", "anomaly", "changepoint")]
    t.loc[b, sensors] = t.loc[a, sensors].to_numpy()          # values copied, timestamps differ
    assert list(splits.find_overlap_groups(t)) == []


def test_overlap_detection_ignores_row_order(splits, tidy):
    t = overlapping(tidy)
    shuffled = t.sample(frac=1.0, random_state=3).reset_index(drop=True)
    assert as_sets(splits.find_overlap_groups(shuffled)) == as_sets(splits.find_overlap_groups(t))


@pytest.mark.parametrize("seed", range(8))
def test_make_splits_keeps_groups_together(splits, tidy, seed):
    t = overlapping(tidy)
    groups = splits.find_overlap_groups(t)
    m = splits.make_splits(t, seed=seed, keep_together=groups)
    side = side_of(m)
    labelled = set(t.loc[t["family"] != "anomaly-free", "experiment_id"])
    assigned = list(m["test"]) + [e for f in m["dev_folds"] for e in f]
    assert sorted(assigned) == sorted(labelled), "every labelled experiment exactly once"
    for group in groups:
        sides = {side[e] for e in group if e in side}
        assert len(sides) == 1, f"group {sorted(group)} is split across {sorted(sides)}"
    assert "other/5" not in m["test"], "an experiment sharing rows with the reference recording is in the test set"
    assert len(m["test"]) >= 2 and all(len(f) > 0 for f in m["dev_folds"])
    splits.validate_splits(m, t)


def test_make_splits_records_groups_and_version(splits, tidy):
    t = overlapping(tidy)
    m = splits.make_splits(t, seed=0, keep_together=splits.find_overlap_groups(t))
    assert m["version"] == "v2"
    assert as_sets(m["overlap_groups"]) == sorted(EXPECTED, key=min)
    assert m["reference_normal"] == [REF]


def test_make_splits_still_stratifies_by_family(splits, tidy):
    t = overlapping(tidy)
    for seed in range(5):
        m = splits.make_splits(t, seed=seed, keep_together=splits.find_overlap_groups(t))
        assert {e.split("/")[0] for e in m["test"]} == {"valve1", "valve2", "other"}, m["test"]


def _separated_manifest(splits, t):
    """A v1-style manifest that separates every planted group."""
    m = splits.make_splits(tidy=t, seed=0)
    ids = sorted(e for e in set(t["experiment_id"]) if e != REF)
    special = {"other/1", "other/2", "other/3", "valve1/0", "valve1/5", "other/5"}
    rest = [e for e in ids if e not in special]
    m["test"] = sorted(["other/1", "valve1/0", "other/5", *rest[:2]])
    folds = [["other/2", "valve1/5"], ["other/3"], [], []]
    for i, e in enumerate(rest[2:]):
        folds[i % 4].append(e)
    m["dev_folds"] = [sorted(f) for f in folds]
    return m


def test_validate_rejects_separated_groups_even_without_the_manifest_key(splits, tidy):
    t = overlapping(tidy)
    m = _separated_manifest(splits, t)
    m.pop("overlap_groups", None)
    with pytest.raises(ValueError):
        splits.validate_splits(m, t)


def test_validate_rejects_reference_overlap_in_test(splits, tidy):
    t = plant_overlap(tidy, REF, "other/5", n=8)
    m = splits.make_splits(t, seed=0, keep_together=splits.find_overlap_groups(t))
    splits.validate_splits(m, t)
    bad = copy.deepcopy(m)
    bad["dev_folds"] = [[e for e in f if e != "other/5"] for f in bad["dev_folds"]]
    bad["test"] = sorted([*bad["test"], "other/5"])
    with pytest.raises(ValueError):
        splits.validate_splits(bad, t)


def test_validate_rejects_group_spread_over_two_dev_folds(splits, tidy):
    t = plant_overlap(tidy, "valve1/1", "valve1/2", n=5)
    m = splits.make_splits(t, seed=0, keep_together=splits.find_overlap_groups(t))
    bad = copy.deepcopy(m)
    bad["test"] = [e for e in bad["test"] if e not in ("valve1/1", "valve1/2")]
    bad["dev_folds"] = [[e for e in f if e not in ("valve1/1", "valve1/2")] for f in bad["dev_folds"]]
    bad["dev_folds"][0].append("valve1/1")
    bad["dev_folds"][1].append("valve1/2")
    with pytest.raises(ValueError):
        splits.validate_splits(bad, t)


def test_validate_accepts_clean_data(splits, tidy):
    splits.validate_splits(splits.make_splits(tidy, seed=1), tidy)


def test_repair_is_minimal_and_never_moves_into_test(splits, tidy):
    t = overlapping(tidy)
    old = _separated_manifest(splits, t)
    frozen = copy.deepcopy(old)
    new = splits.repair_splits(old, splits.find_overlap_groups(t))
    assert old == frozen, "repair_splits must not modify its input"
    splits.validate_splits(new, t)
    assert set(new["test"]) <= set(old["test"]), "the repair moved a development experiment into the test set"
    before, after = side_of(old), side_of(new)
    assert sorted(after) == sorted(before), "experiments were lost or invented"
    grouped = {e for g in EXPECTED for e in g}
    moved = {e for e in before if before[e] != after[e]}
    assert moved <= grouped, f"experiments outside any overlap group were moved: {sorted(moved - grouped)}"
    assert new["version"] == "v2" and as_sets(new["overlap_groups"]) == sorted(EXPECTED, key=min)


def test_repair_leaves_a_valid_manifest_alone(splits, tidy):
    t = overlapping(tidy)
    good = splits.make_splits(t, seed=2, keep_together=splits.find_overlap_groups(t))
    again = splits.repair_splits(good, splits.find_overlap_groups(t))
    assert side_of(again) == side_of(good)


def test_repair_keeps_group_that_is_entirely_in_test(splits, tidy):
    t = plant_overlap(tidy, "valve1/1", "valve1/2", n=5)
    m = splits.make_splits(tidy, seed=0)
    for e in ("valve1/1", "valve1/2"):
        m["dev_folds"] = [[x for x in f if x != e] for f in m["dev_folds"]]
        if e not in m["test"]:
            m["test"].append(e)
    new = splits.repair_splits(m, splits.find_overlap_groups(t))
    assert {"valve1/1", "valve1/2"} <= set(new["test"])
