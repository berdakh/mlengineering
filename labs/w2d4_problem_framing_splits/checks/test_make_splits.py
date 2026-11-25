"""Contract of make_splits: a leak-free, stratified, reproducible partition of EXPERIMENTS."""
from __future__ import annotations

from collections import Counter

import pytest

from conftest import DEFAULT_SIZES, assigned_ids, labelled_ids, synth_tidy

SEEDS = range(10)


@pytest.mark.parametrize("seed", SEEDS)
def test_every_labelled_experiment_is_assigned_exactly_once(splits, tidy, seed):
    manifest = splits.make_splits(tidy, seed=seed)
    counts = Counter(assigned_ids(manifest))
    repeated = sorted(e for e, c in counts.items() if c > 1)
    assert not repeated, f"experiments on more than one side of the split: {repeated}"
    assert set(counts) == labelled_ids(tidy), "test + dev folds must cover exactly the labelled experiments"


def test_entries_are_experiment_ids_not_rows(splits, tidy):
    manifest = splits.make_splits(tidy, seed=0)
    assert manifest["unit"] == "experiment_id"
    assert all(isinstance(e, str) for e in assigned_ids(manifest))


@pytest.mark.parametrize("seed", SEEDS)
def test_test_set_is_stratified_by_family(splits, tidy, seed):
    manifest = splits.make_splits(tidy, seed=seed)
    dev = {e for fold in manifest["dev_folds"] for e in fold}
    for family, n in DEFAULT_SIZES.items():
        if n < 2:
            continue
        in_test = [e for e in manifest["test"] if e.startswith(family + "/")]
        in_dev = [e for e in dev if e.startswith(family + "/")]
        assert in_test, f"seed {seed}: family '{family}' has no experiment in the test set"
        assert in_dev, f"seed {seed}: family '{family}' has no experiment left for development"


def test_test_fraction_is_respected_approximately(splits, tidy):
    n = len(labelled_ids(tidy))
    for fraction in (0.25, 0.5):
        manifest = splits.make_splits(tidy, seed=0, test_fraction=fraction)
        assert abs(len(manifest["test"]) - fraction * n) <= len(DEFAULT_SIZES), (
            f"test_fraction={fraction}: got {len(manifest['test'])} of {n} experiments in test")


@pytest.mark.parametrize("n_folds", [2, 4])
def test_dev_folds_are_nonempty_and_balanced(splits, tidy, n_folds):
    manifest = splits.make_splits(tidy, seed=0, n_folds=n_folds)
    sizes = [len(f) for f in manifest["dev_folds"]]
    assert len(sizes) == n_folds
    assert min(sizes) >= 1, f"empty dev fold: {sizes}"
    assert max(sizes) - min(sizes) <= len(DEFAULT_SIZES), f"badly unbalanced dev folds: {sizes}"


def test_same_seed_gives_same_manifest(splits, tidy):
    assert splits.make_splits(tidy, seed=3) == splits.make_splits(tidy, seed=3)


def test_result_does_not_depend_on_row_order(splits, tidy):
    shuffled = tidy.sample(frac=1.0, random_state=1).reset_index(drop=True)
    a, b = splits.make_splits(tidy, seed=3), splits.make_splits(shuffled, seed=3)
    assert sorted(a["test"]) == sorted(b["test"]), "the split changed when the rows were reordered"
    assert sorted(map(sorted, a["dev_folds"])) == sorted(map(sorted, b["dev_folds"]))


def test_seed_is_actually_used(splits, tidy):
    test_sets = {tuple(sorted(splits.make_splits(tidy, seed=s)["test"])) for s in range(6)}
    assert len(test_sets) >= 2, "six different seeds produced the same test set"
    assert splits.make_splits(tidy, seed=5)["seed"] == 5


def test_fault_free_recording_is_reference_only(splits, tidy):
    manifest = splits.make_splits(tidy, seed=0)
    assert manifest["reference_normal"] == ["anomaly-free/anomaly-free"]
    assert not [e for e in assigned_ids(manifest) if e.startswith("anomaly-free")], (
        "the fault-free recording has no positive samples; it must not be in test or dev folds")


def test_works_without_a_fault_free_recording(splits):
    manifest = splits.make_splits(synth_tidy(with_normal=False), seed=0)
    assert manifest["reference_normal"] == []


def test_manifest_has_the_agreed_fields(splits, tidy):
    manifest = splits.make_splits(tidy, seed=0)
    assert {"version", "seed", "unit", "test", "dev_folds", "reference_normal", "protocol_b"} <= set(manifest)
    assert manifest["version"] == "v1"
    assert manifest["protocol_b"]["holdout_family"] == "other"
