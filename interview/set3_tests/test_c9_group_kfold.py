"""C9: grouped K-fold from scratch. Contract tests; any correct assignment strategy passes."""
import random

import pytest


def make_groups(seed, n_groups=12, lo=1, hi=30):
    rng = random.Random(seed)
    groups = []
    for g in range(n_groups):
        groups += [f"g{g:02d}"] * rng.randint(lo, hi)
    rng.shuffle(groups)
    return groups


def folds_of(c9, groups, k, seed=0):
    out = list(c9.group_kfold(groups, k, seed=seed))
    assert len(out) == k, "must yield exactly k (train_idx, test_idx) pairs"
    return [(list(tr), list(te)) for tr, te in out]


@pytest.mark.parametrize("seed", range(5))
@pytest.mark.parametrize("k", [2, 3, 5])
def test_partition_and_no_group_on_both_sides(c9, seed, k):
    groups = make_groups(seed)
    n = len(groups)
    seen = []
    for train, test in folds_of(c9, groups, k):
        assert sorted(train + test) == list(range(n)), "train and test must partition all row indices"
        assert not ({groups[i] for i in train} & {groups[i] for i in test}), "a group is on both sides"
        assert test, "empty test fold"
        seen += test
    assert sorted(seen) == list(range(n)), "every row must be a test row exactly once"


def test_whole_groups_stay_together_even_when_rows_are_interleaved(c9):
    groups = ["a", "b", "a", "c", "b", "a", "c", "d", "d", "a"]
    for train, test in folds_of(c9, groups, 2):
        for g in set(groups):
            idx = {i for i, x in enumerate(groups) if x == g}
            assert idx <= set(train) or idx <= set(test)


def test_deterministic_for_a_seed_and_seed_changes_assignment(c9):
    groups = make_groups(3, n_groups=20)
    a = folds_of(c9, groups, 4, seed=11)
    b = folds_of(c9, groups, 4, seed=11)
    assert a == b, "same seed must give the same folds"
    canon = lambda folds: sorted(tuple(sorted(te)) for _, te in folds)  # noqa: E731
    different = [canon(folds_of(c9, groups, 4, seed=s)) != canon(a) for s in (1, 2, 3, 4, 5)]
    assert any(different), "the seed has no effect on which groups share a fold"


def test_fold_sizes_are_reasonably_balanced_in_rows(c9):
    # 4 big groups and 16 small ones: assigning groups without regard to size can put
    # all big groups in one fold. Greedy largest-first gets within one small group of even.
    groups = []
    for g in range(4):
        groups += [f"big{g}"] * 100
    for g in range(16):
        groups += [f"small{g}"] * 10
    sizes = [len(te) for _, te in folds_of(c9, groups, 4)]
    assert max(sizes) - min(sizes) <= 20, f"row counts per fold too uneven: {sizes}"


def test_errors(c9):
    with pytest.raises(ValueError):
        list(c9.group_kfold(["a", "a", "b"], 3))      # more folds than groups
    with pytest.raises(ValueError):
        list(c9.group_kfold(["a", "b"], 1))           # k must be >= 2


def test_accepts_non_string_group_ids_and_k_equal_number_of_groups(c9):
    groups = [3, 1, 2, 3, 1, 2, 2]
    folds = folds_of(c9, groups, 3)
    assert sorted(len(te) for _, te in folds) == [2, 2, 3]
