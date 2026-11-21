import pandas as pd

from split_impl import train_test_split_by_date


def test_split_works():
    df = pd.DataFrame({"snapshot_date": ["2025-01-01", "2025-02-01", "2025-03-01", "2025-04-01"], "x": [1, 2, 3, 4]})
    train, test = train_test_split_by_date(df, "2025-02-15")
    assert len(train) == 2 and len(test) == 2
    assert train.x.max() < test.x.min()
