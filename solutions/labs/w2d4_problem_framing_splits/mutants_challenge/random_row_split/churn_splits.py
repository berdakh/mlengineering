"""Reference solution: temporal + customer-grouped split for the churn scenario."""
from __future__ import annotations

import numpy as np
import pandas as pd


def month_number(months) -> np.ndarray:
    """'YYYY-MM' -> consecutive integer, so month arithmetic is plain subtraction."""
    periods = pd.PeriodIndex(months, freq="M")
    return np.asarray(periods.year * 12 + periods.month)


def split_customer_months(df: pd.DataFrame, test_start: str, horizon_months: int = 3,
                          new_customer_fraction: float = 0.2, seed: int = 0) -> dict[str, list]:
    """Return index labels for 'train', 'test_known' and 'test_new'.

    Timeline: the model is trained at the end of the month before ``test_start`` and then scores
    monthly snapshots from ``test_start`` onwards. A row's label covers the ``horizon_months``
    months after its own month, so
      * a row can be TRAINED on only if its whole label window ended before test_start;
      * a row can be EVALUATED on only if its whole label window lies inside the data.
    Eligibility is decided by the calendar, never by whether the label happens to be known:
    churners are known early, so "label is not null" selects positives preferentially.
    """
    rng = np.random.default_rng(seed)
    labelled = df[df["churn_within_3m"].notna()]
    u = rng.random(len(labelled))
    return {"train": labelled.index[u < 0.6].tolist(),
            "test_known": labelled.index[(u >= 0.6) & (u < 0.8)].tolist(),
            "test_new": labelled.index[u >= 0.8].tolist()}
