"""The function under test. This implementation is believed correct - read it, do not edit it.
Your tests in test_split.py will ALSO be run against several subtly broken versions of this
function; good tests fail on those."""
from __future__ import annotations

import pandas as pd


def train_test_split_by_date(df: pd.DataFrame, cutoff, date_col: str = "snapshot_date"):
    """Split rows into (train, test) by time.

    * train = rows with date strictly before `cutoff`; test = rows on or after `cutoff`.
    * `cutoff` may be a string or a Timestamp; `date_col` may hold strings or datetimes.
    * Every input row appears in exactly one output; columns, dtypes and the original
      relative order of rows are preserved.
    * The input frame is not modified.
    * Raises KeyError if `date_col` is missing, ValueError if train or test would be empty.
    """
    if date_col not in df.columns:
        raise KeyError(date_col)
    dates = pd.to_datetime(df[date_col])
    is_test = dates >= pd.Timestamp(cutoff)
    train, test = df[~is_test], df[is_test]
    if train.empty or test.empty:
        raise ValueError(f"cutoff {cutoff!r} leaves an empty train or test set")
    return train, test
