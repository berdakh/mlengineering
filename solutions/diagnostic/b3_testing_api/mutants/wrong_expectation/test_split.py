import pandas as pd
import pytest

from split_impl import train_test_split_by_date


def test_cutoff_row_in_train():
    df = pd.DataFrame({"snapshot_date": ["2025-01-01", "2025-02-01", "2025-03-01"], "x": [1, 2, 3]})
    train, test = train_test_split_by_date(df, "2025-02-01")
    assert len(train) == 2 and len(test) == 1   # misreads the spec: cutoff rows belong to test


def test_empty_raises():
    df = pd.DataFrame({"snapshot_date": ["2025-01-01"], "x": [1]})
    with pytest.raises(ValueError):
        train_test_split_by_date(df, "2024-01-01")
