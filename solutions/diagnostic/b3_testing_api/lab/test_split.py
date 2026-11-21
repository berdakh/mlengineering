"""b3 reference tests for train_test_split_by_date: one test per clause of the specification."""
import pandas as pd
import pytest

from split_impl import train_test_split_by_date


@pytest.fixture()
def df():
    # deliberately NOT sorted by date, with two rows exactly at the cutoff used below
    return pd.DataFrame({
        "customer_id": ["a", "b", "c", "d", "e", "f"],
        "snapshot_date": ["2025-03-01", "2025-01-01", "2025-02-01", "2025-02-01", "2025-04-01", "2025-01-01"],
        "x": [3.0, 1.0, 2.0, 2.5, 4.0, 1.5],
    })


def test_rows_before_cutoff_train_rest_test(df):
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert sorted(train.customer_id) == ["b", "f"]
    assert sorted(test.customer_id) == ["a", "c", "d", "e"]


def test_cutoff_rows_belong_to_test(df):
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert {"c", "d"} <= set(test.customer_id)
    assert not {"c", "d"} & set(train.customer_id)


def test_every_row_in_exactly_one_side(df):
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert len(train) + len(test) == len(df)
    assert sorted(list(train.customer_id) + list(test.customer_id)) == sorted(df.customer_id)


def test_order_and_columns_preserved(df):
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert list(train.columns) == list(df.columns) == list(test.columns)
    assert list(test.customer_id) == ["a", "c", "d", "e"]  # original relative order
    assert list(train.customer_id) == ["b", "f"]


def test_input_not_modified(df):
    before = df.copy(deep=True)
    train_test_split_by_date(df, "2025-02-01")
    pd.testing.assert_frame_equal(df, before)  # same values, same order, same dtypes


@pytest.mark.parametrize("cutoff", ["2025-02-01", pd.Timestamp("2025-02-01")])
def test_cutoff_as_string_or_timestamp(df, cutoff):
    train, test = train_test_split_by_date(df, cutoff)
    assert (len(train), len(test)) == (2, 4)


def test_datetime_column_accepted(df):
    df = df.assign(snapshot_date=pd.to_datetime(df.snapshot_date))
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert (len(train), len(test)) == (2, 4)


@pytest.mark.parametrize("cutoff", ["2024-01-01", "2025-01-01", "2026-01-01"])
def test_empty_side_raises(df, cutoff):
    # before all data -> empty train; at the first date -> empty train; after all data -> empty test
    with pytest.raises(ValueError):
        train_test_split_by_date(df, cutoff)


def test_missing_date_column_raises(df):
    with pytest.raises(KeyError):
        train_test_split_by_date(df, "2025-02-01", date_col="nope")


def test_custom_date_column(df):
    train, test = train_test_split_by_date(df.rename(columns={"snapshot_date": "ts"}), "2025-02-01", date_col="ts")
    assert (len(train), len(test)) == (2, 4)
