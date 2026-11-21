"""a3 reference solution: clean the dirty signups export."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "signups_dirty.csv"
if not RAW_PATH.is_file():  # this file lives under solutions/; the data lives under diagnostic/
    RAW_PATH = Path(__file__).resolve().parents[4] / "diagnostic" / "data" / "signups_dirty.csv"
OUTPUT_COLUMNS = ["customer_id", "signup_date", "country", "plan", "monthly_price_usd", "age"]
VALID_PLANS = {"basic", "standard", "premium"}
MISSING_COUNTRY = {"", "UNKNOWN", "-"}
AGE_MISSING_CODES = {-1, 999}
AGE_RANGE = (13, 110)


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def parse_signup_date(s: pd.Series) -> pd.Series:
    """Three explicit formats; anything else becomes NaT instead of being guessed."""
    s = s.str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    iso = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    dmy = s.str.fullmatch(r"\d{2}/\d{2}/\d{4}", na=False)
    stamp = s.str.contains("T", na=False)
    out[iso] = pd.to_datetime(s[iso], format="%Y-%m-%d").astype("datetime64[ns]")
    out[dmy] = pd.to_datetime(s[dmy], format="%d/%m/%Y").astype("datetime64[ns]")
    # offsets differ per row -> convert every value to UTC first, then take the calendar date
    utc = pd.to_datetime(s[stamp], utc=True, format="%Y-%m-%dT%H:%M:%S%z")
    out[stamp] = utc.dt.tz_localize(None).dt.normalize().astype("datetime64[ns]")
    return out


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # 1. one row per customer: the most recently updated version wins
    df["_updated"] = pd.to_datetime(df["updated_at"], format="%Y-%m-%d %H:%M:%S")
    df = (df.sort_values(["customer_id", "_updated"], kind="stable")
            .drop_duplicates("customer_id", keep="last"))

    # 2. dates
    df["signup_date"] = parse_signup_date(df["signup_date"])

    # 3. categoricals: normalise, then map everything outside the known vocabulary to missing
    country = df["country"].fillna("").str.strip().str.upper()
    df["country"] = country.where(~country.isin(MISSING_COUNTRY), None)
    plan = df["plan"].fillna("").str.strip().str.lower()
    df["plan"] = plan.where(plan.isin(VALID_PLANS), None)

    # 4. price: strip the currency symbol, convert cents to dollars using the unit column
    price = pd.to_numeric(df["monthly_price"].str.replace("$", "", regex=False).str.strip(), errors="coerce")
    is_cents = df["price_unit"].str.strip().str.lower().eq("cents")
    df["monthly_price_usd"] = np.where(is_cents, price / 100.0, price).round(2)

    # 5. age: sentinel codes and impossible values are missing, not numbers
    age = pd.to_numeric(df["age"], errors="coerce")
    bad = age.isin(AGE_MISSING_CODES) | (age < AGE_RANGE[0]) | (age > AGE_RANGE[1])
    df["age"] = age.mask(bad)

    return df[OUTPUT_COLUMNS].sort_values("customer_id").reset_index(drop=True)


if __name__ == "__main__":
    out = clean(load_raw())
    print(out.head(10))
    print(out.dtypes)
    print(out.isna().sum())
