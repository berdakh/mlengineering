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
    m = month_number(df["month"])
    start = int(month_number([test_start])[0])
    last = int(m.max())
    customer = df["customer_id"].to_numpy()

    can_train = m + horizon_months < start
    can_test = (m >= start) & (m + horizon_months <= last)

    candidates = np.array(sorted(set(customer[can_train])))
    n_held = int(round(new_customer_fraction * len(candidates)))
    held_out = set(np.random.default_rng(seed).choice(candidates, size=n_held, replace=False).tolist())

    in_train = can_train
    seen = set(customer[in_train]) - held_out
    known = can_test & np.isin(customer, list(seen))
    new = can_test & ~np.isin(customer, list(seen))      # held out by design OR joined too late
    return {"train": df.index[in_train].tolist(),
            "test_known": df.index[known].tolist(),
            "test_new": df.index[new].tolist()}
