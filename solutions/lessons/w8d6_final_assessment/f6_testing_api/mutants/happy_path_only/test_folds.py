"""Weak suite: only checks that the function runs and returns ids in range."""
import pandas as pd

from fold_impl import assign_folds_by_group


def test_runs():
    df = pd.DataFrame({"account": ["a", "b", "c", "d", "a"], "x": range(5)})
    folds = assign_folds_by_group(df, "account", 2)
    assert len(folds) == 5 and set(folds) <= {0, 1}
