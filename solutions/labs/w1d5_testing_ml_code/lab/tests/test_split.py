"""Structural guarantees of the group split. None of these looks at a metric."""
import numpy as np
import pandas as pd
import pytest

from pumpwatch.split import group_train_test_split


@pytest.fixture
def features() -> pd.DataFrame:
    units = [f"U{u:02d}" for u in range(10)]
    return pd.DataFrame({
        "unit_id": np.repeat(units, 6),
        "window_id": np.tile(np.arange(6), 10),
        "label": np.tile([0, 0, 0, 1, 1, 1], 10),
    })


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_no_unit_on_both_sides(features, seed):
    train_idx, test_idx = group_train_test_split(features, test_fraction=0.3, seed=seed)
    train_units = set(features["unit_id"].iloc[train_idx])
    test_units = set(features["unit_id"].iloc[test_idx])
    assert train_units and test_units
    assert train_units.isdisjoint(test_units)


def test_split_is_a_partition_of_the_rows(features):
    train_idx, test_idx = group_train_test_split(features, test_fraction=0.3, seed=0)
    assert sorted(np.concatenate([train_idx, test_idx]).tolist()) == list(range(len(features)))


def test_test_fraction_is_respected_at_unit_level(features):
    _, test_idx = group_train_test_split(features, test_fraction=0.3, seed=0)
    assert features["unit_id"].iloc[test_idx].nunique() == 3


def test_same_seed_same_split(features):
    a = group_train_test_split(features, seed=11)
    b = group_train_test_split(features, seed=11)
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])


def test_seed_argument_is_honoured(features):
    # 10 seeds, 120 possible test sets: a constant result means the seed is ignored.
    test_sets = {
        tuple(sorted(set(features["unit_id"].iloc[group_train_test_split(features, seed=s)[1]])))
        for s in range(10)
    }
    assert len(test_sets) > 1
