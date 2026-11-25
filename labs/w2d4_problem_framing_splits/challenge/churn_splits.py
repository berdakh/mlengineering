"""Challenge starter: implement split_customer_months (see README.md in this directory)."""
from __future__ import annotations

import pandas as pd


def split_customer_months(df: pd.DataFrame, test_start: str, horizon_months: int = 3,
                          new_customer_fraction: float = 0.2, seed: int = 0) -> dict[str, list]:
    """Return {'train': [...], 'test_known': [...], 'test_new': [...]} of ``df.index`` labels."""
    raise NotImplementedError
