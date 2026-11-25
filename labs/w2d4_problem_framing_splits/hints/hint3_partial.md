# Hint 3 - partial implementation (challenge)

The skeleton below is complete except for the three marked expressions.

```python
import numpy as np
import pandas as pd


def month_number(months):
    p = pd.PeriodIndex(months, freq="M")
    return np.asarray(p.year * 12 + p.month)


def split_customer_months(df, test_start, horizon_months=3, new_customer_fraction=0.2, seed=0):
    m = month_number(df["month"])
    start = int(month_number([test_start])[0])
    last = int(m.max())
    customer = df["customer_id"].to_numpy()

    can_train = ...   # (1) label window closed before `start`
    can_test = ...    # (2) at/after `start` AND label window closes by `last`

    candidates = np.array(sorted(set(customer[can_train])))
    n_held = int(round(new_customer_fraction * len(candidates)))
    held_out = set(np.random.default_rng(seed).choice(candidates, size=n_held, replace=False).tolist())

    in_train = can_train & ~np.isin(customer, list(held_out))
    seen = ...        # (3) customers that actually have a row in the training set
    known = can_test & np.isin(customer, list(seen))
    new = can_test & ~np.isin(customer, list(seen))
    return {"train": df.index[in_train].tolist(),
            "test_known": df.index[known].tolist(),
            "test_new": df.index[new].tolist()}
```

Self-check before running the checks: with the supplied file and `test_start="2025-01"` the training
months should end at 2024-09 and the test months should be 2025-01 to 2025-03.

The full reference is in `solutions/labs/w2d4_problem_framing_splits/challenge/`.
