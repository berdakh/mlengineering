"""f6 reference tests for assign_folds_by_group: one test per clause of the specification."""
import pandas as pd
import pytest

from fold_impl import assign_folds_by_group


@pytest.fixture()
def df():
    # 8 groups of uneven size, rows not ordered by group, a non-default index
    groups = ["g3", "g1", "g3", "g2", "g8", "g5", "g1", "g4", "g6", "g7", "g3", "g8", "g2", "g5"]
    return pd.DataFrame({"account": groups, "x": range(len(groups))}, index=range(100, 100 + len(groups)))


def test_one_fold_id_per_row_in_range_and_index_kept(df):
    folds = assign_folds_by_group(df, "account", 4)
    assert list(folds.index) == list(df.index)
    assert set(folds.unique()) <= set(range(4))


def test_every_group_in_exactly_one_fold(df):
    folds = assign_folds_by_group(df, "account", 4)
    per_group = folds.groupby(df["account"]).nunique()
    assert (per_group == 1).all()


def test_every_fold_non_empty(df):
    assert set(assign_folds_by_group(df, "account", 4).unique()) == {0, 1, 2, 3}


def test_same_seed_same_folds_even_if_rows_reordered(df):
    a = assign_folds_by_group(df, "account", 4, seed=7)
    b = assign_folds_by_group(df, "account", 4, seed=7)
    shuffled = df.sample(frac=1.0, random_state=1)
    c = assign_folds_by_group(shuffled, "account", 4, seed=7)
    assert a.equals(b)
    assert (c.groupby(shuffled["account"]).first() == a.groupby(df["account"]).first()).all()


def test_input_not_modified(df):
    before = df.copy()
    assign_folds_by_group(df, "account", 4)
    pd.testing.assert_frame_equal(df, before)


def test_errors(df):
    with pytest.raises(KeyError):
        assign_folds_by_group(df, "missing_column", 4)
    with pytest.raises(ValueError):
        assign_folds_by_group(df, "account", 9)      # 8 groups
    with pytest.raises(ValueError):
        assign_folds_by_group(df, "account", 1)
