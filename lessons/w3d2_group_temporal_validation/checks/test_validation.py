"""Contracts of flowguard.validation. Offline, deterministic, SYNTHETIC inputs only."""
from __future__ import annotations

import copy

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold

import synth


# ----------------------------------------------------------------------------- required_purge
@pytest.mark.parametrize("window, horizon, expected", [(1, 0, 0), (30, 0, 29), (1, 5, 5), (40, 30, 69)])
def test_required_purge_counts_shared_raw_samples(validation, window, horizon, expected):
    assert validation.required_purge(window, horizon) == expected


def test_required_purge_is_exactly_the_dependence_range(validation):
    """Row i is built from raw samples [i - w + 1, i + h]. With the returned buffer no training row
    may share a sample with a test row; with one row less, at least one pair must."""
    w, h, n = 7, 4, 120
    span = lambda i: set(range(i - w + 1, i + h + 1))  # noqa: E731
    buffer = validation.required_purge(w, h)
    for train, test in validation.purged_time_split(n, 4, purge=buffer, embargo=buffer):
        test_samples = set().union(*(span(j) for j in test))
        assert all(not (span(i) & test_samples) for i in train)
    shares = False
    for train, test in validation.purged_time_split(n, 4, purge=buffer - 1, embargo=buffer - 1):
        test_samples = set().union(*(span(j) for j in test))
        shares |= any(span(i) & test_samples for i in train)
    assert shares, "a buffer one row shorter should leave shared samples; is the returned buffer too long?"


@pytest.mark.parametrize("window, horizon", [(0, 0), (5, -1)])
def test_required_purge_rejects_impossible_arguments(validation, window, horizon):
    with pytest.raises(ValueError):
        validation.required_purge(window, horizon)


# ----------------------------------------------------------------------------- group_kfold_indices
def _groups(seed=0, n_groups=17):
    rng = np.random.default_rng(seed)
    labels = np.array([f"m{k:02d}" for k in range(n_groups)])
    return labels[rng.integers(0, n_groups, 400)]


def test_group_kfold_never_splits_a_group_and_validates_each_once(validation):
    groups = _groups()
    folds = validation.group_kfold_indices(groups, 5, seed=0)
    assert len(folds) == 5
    validated = np.concatenate([val for _, val in folds])
    assert sorted(validated.tolist()) == list(range(len(groups))), "every row must be validated exactly once"
    seen_groups: list[str] = []
    for train, val in folds:
        assert not set(train) & set(val)
        assert sorted(set(train) | set(val)) == list(range(len(groups)))
        assert not set(groups[train]) & set(groups[val]), "a group is on both sides of a fold"
        seen_groups += sorted(set(groups[val]))
    assert sorted(seen_groups) == sorted(set(groups)), "each group must be held out in exactly one fold"


def test_group_kfold_is_deterministic_and_seeded(validation):
    groups = _groups()
    a = validation.group_kfold_indices(groups, 4, seed=3)
    b = validation.group_kfold_indices(groups, 4, seed=3)
    for (tr_a, va_a), (tr_b, va_b) in zip(a, b):
        assert np.array_equal(tr_a, tr_b) and np.array_equal(va_a, va_b)
    partition = lambda folds: sorted(tuple(sorted(set(groups[v]))) for _, v in folds)  # noqa: E731
    others = [partition(validation.group_kfold_indices(groups, 4, seed=s)) for s in (11, 12, 13)]
    assert any(o != partition(a) for o in others), "the seed has no effect on which groups go together"


def test_group_kfold_rejects_more_folds_than_groups(validation):
    with pytest.raises(ValueError):
        validation.group_kfold_indices(["a", "a", "b", "b"], 3)


def test_grouped_estimate_recovers_truth_where_row_kfold_is_optimistic(validation):
    """Planted within-machine effect. Truth = accuracy on 400 machines never seen in any form.

    The tolerance (0.08) covers the spread of a grouped estimate over different valid assignments of
    machines to folds (about 0.63-0.67 here); row-wise K-fold reports about 0.89 against a truth of 0.63."""
    X, y, groups = synth.machines(80, 25, seed=9)
    X_new, y_new, _ = synth.machines(400, 25, seed=109)
    model = lambda: RandomForestClassifier(n_estimators=40, min_samples_leaf=3, random_state=0, n_jobs=1)  # noqa: E731

    def cv(folds) -> float:
        return float(np.mean([np.mean(model().fit(X[tr], y[tr]).predict(X[va]) == y[va]) for tr, va in folds]))

    truth = float(np.mean(model().fit(X, y).predict(X_new) == y_new))
    by_row = cv(KFold(5, shuffle=True, random_state=0).split(X))
    by_group = cv(validation.group_kfold_indices(groups, 5, seed=0))
    assert by_row - truth > 0.15, "the planted effect should make row-wise K-fold optimistic (check the fixture)"
    assert abs(by_group - truth) < 0.08, (
        f"grouped estimate {by_group:.3f} is not close to the truth on new machines {truth:.3f} "
        f"(row-wise K-fold gives {by_row:.3f})")


# ----------------------------------------------------------------------------- grouped_folds
def test_grouped_folds_use_the_manifest_dev_folds_only(validation):
    manifest = synth.manifest()
    folds = validation.grouped_folds(manifest)
    dev = sorted(e for fold in manifest["dev_folds"] for e in fold)
    assert len(folds) == len(manifest["dev_folds"])
    assert sorted(e for _, val in folds for e in val) == dev, "each development experiment is validated once"
    for (train, val), expected_val in zip(folds, manifest["dev_folds"]):
        assert sorted(val) == sorted(expected_val), "fold k must validate on the manifest's fold k"
        assert not set(train) & set(val)
        assert sorted(set(train) | set(val)) == dev
        assert not set(train) & set(manifest["test"]), "test experiments must never be trained on"
        assert not (set(train) | set(val)) & set(manifest["reference_normal"])


def test_grouped_folds_reject_a_separated_overlap_group(validation):
    manifest = synth.manifest()
    manifest["dev_folds"] = [["other/0", "valve1/0"], ["other/1", "valve1/1", "valve2/0"], ["other/2", "valve1/2", "valve2/1"]]
    with pytest.raises(ValueError):
        validation.grouped_folds(manifest)


def test_grouped_folds_reject_a_test_experiment_among_the_folds(validation):
    manifest = synth.manifest()
    manifest["dev_folds"][0] = manifest["dev_folds"][0] + ["valve1/9"]
    with pytest.raises(ValueError):
        validation.grouped_folds(manifest)


def test_grouped_folds_do_not_modify_the_manifest(validation):
    manifest = synth.manifest()
    before = copy.deepcopy(manifest)
    validation.grouped_folds(manifest)
    assert manifest == before


# ----------------------------------------------------------------------------- leave_one_family_out
def test_each_labelled_family_is_held_out_once_and_completely(validation):
    tidy = synth.tidy(synth.FAMILY_TIDY)
    result = validation.leave_one_family_out(tidy)
    assert sorted(family for family, _, _ in result) == ["other", "valve1", "valve2"]
    for family, train, val in result:
        expected = sorted(e for e in synth.FAMILY_TIDY if e.startswith(family + "/"))
        assert sorted(val) == expected, f"holding out {family} must validate on all of it and nothing else"
        assert all(not e.startswith(family + "/") for e in train)
        assert "anomaly-free/anomaly-free" not in train and "anomaly-free/anomaly-free" not in val
        assert sorted(set(train) | set(val)) == sorted(e for e in synth.FAMILY_TIDY if not e.startswith("anomaly-free"))


def test_family_holdout_drops_training_experiments_that_overlap_the_held_out_family(validation):
    tidy = synth.tidy(synth.FAMILY_TIDY)
    result = {family: (train, val) for family, train, val in
              validation.leave_one_family_out(tidy, keep_together=[{"valve1/2", "other/0"}])}
    assert "other/0" not in result["valve1"][0], "other/0 shares rows with held-out valve1/2"
    assert "valve1/2" not in result["other"][0], "valve1/2 shares rows with held-out other/0"
    assert {"valve1/2", "other/0"} <= set(result["valve2"][0]), "the group is intact when neither member is held out"
    assert "other/1" in result["valve1"][0], "only the overlapping experiment is dropped, not its family"


# ----------------------------------------------------------------------------- purged_time_split
@pytest.mark.parametrize("n, n_splits, purge, embargo", [(100, 4, 0, 0), (103, 5, 7, 0), (103, 5, 0, 9), (240, 6, 12, 5)])
def test_purged_split_blocks_and_buffers(validation, n, n_splits, purge, embargo):
    folds = validation.purged_time_split(n, n_splits, purge=purge, embargo=embargo)
    assert len(folds) == n_splits
    assert np.concatenate([test for _, test in folds]).tolist() == list(range(n)), (
        "test blocks must be contiguous, in time order, and together cover every row exactly once")
    for train, test in folds:
        start, stop = int(test[0]), int(test[-1])
        assert np.array_equal(test, np.arange(start, stop + 1)), "a test block must be contiguous"
        expected = [i for i in range(n) if i < start - purge or i > stop + embargo]
        assert sorted(np.asarray(train).tolist()) == expected, (
            f"block {start}..{stop}: training must be every row except the block, the {purge} rows "
            f"before it and the {embargo} rows after it")


def test_purged_split_block_sizes_are_balanced(validation):
    sizes = [len(test) for _, test in validation.purged_time_split(103, 5)]
    assert max(sizes) - min(sizes) <= 1 and sum(sizes) == 103


@pytest.mark.parametrize("kwargs", [{"purge": -1}, {"embargo": -3}])
def test_purged_split_rejects_negative_buffers(validation, kwargs):
    with pytest.raises(ValueError):
        validation.purged_time_split(50, 5, **kwargs)


def test_purged_split_rejects_too_many_splits(validation):
    with pytest.raises(ValueError):
        validation.purged_time_split(3, 5)


# ----------------------------------------------------------------------------- forward_chaining_split
@pytest.mark.parametrize("n, n_splits, gap", [(100, 4, 0), (100, 4, 6), (57, 3, 2)])
def test_forward_chaining_trains_strictly_before_the_test_block(validation, n, n_splits, gap):
    folds = validation.forward_chaining_split(n, n_splits, gap=gap)
    assert len(folds) == n_splits
    previous_stop, previous_train = -1, 0
    for train, test in folds:
        start, stop = int(test[0]), int(test[-1])
        assert np.array_equal(test, np.arange(start, stop + 1))
        assert start > previous_stop, "test blocks must move forward in time without overlapping"
        assert np.array_equal(train, np.arange(0, start - gap)), (
            "training must be every row from the start of the series up to `gap` rows before the block")
        assert len(train) > previous_train, "the training window must expand from fold to fold"
        previous_stop, previous_train = stop, len(train)
    assert previous_stop == n - 1, "the last test block must end at the last row"


def test_forward_chaining_rejects_a_gap_that_leaves_nothing_to_train_on(validation):
    with pytest.raises(ValueError):
        validation.forward_chaining_split(20, 4, gap=10)
    with pytest.raises(ValueError):
        validation.forward_chaining_split(20, 4, gap=-1)
