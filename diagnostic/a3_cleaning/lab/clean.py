"""a3: clean the dirty signups export. Implement `clean`; see ../README.md for the contract."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "signups_dirty.csv"
OUTPUT_COLUMNS = ["customer_id", "signup_date", "country", "plan", "monthly_price_usd", "age"]


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read every column as text so nothing is silently coerced. (Provided - do not change.)"""
    return pd.read_csv(path, dtype=str)


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Return one cleaned row per customer with OUTPUT_COLUMNS. Must not modify `raw`."""
    raise NotImplementedError


if __name__ == "__main__":
    out = clean(load_raw())
    print(out.head(10))
    print(out.dtypes)
    print(out.isna().sum())
