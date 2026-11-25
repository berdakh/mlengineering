"""f3 reference solution: clean the dirty accounts export."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

RAW_PATH = Path(__file__).resolve().parents[2] / "data" / "accounts_dirty.csv"
if not RAW_PATH.is_file():  # this file lives under solutions/; the data lives under lessons/
    RAW_PATH = Path(__file__).resolve().parents[5] / "labs" / "w8d6_final_assessment" / "data" / "accounts_dirty.csv"
OUTPUT_COLUMNS = ["account_id", "signup_date", "region", "tier", "monthly_fee_usd", "employees"]
VALID_TIERS = {"starter", "business", "enterprise"}
MISSING_REGION = {"", "N/A", "?"}
EMPLOYEE_CODES = {-1, 99999}
EMPLOYEE_RANGE = (1, 50_000)


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str)


def parse_signup_date(s: pd.Series) -> pd.Series:
    """Three explicit formats; anything else becomes NaT instead of being guessed."""
    s = s.str.strip()
    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")
    iso = s.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False)
    dmy = s.str.fullmatch(r"\d{2}\.\d{2}\.\d{4}", na=False)
    stamp = s.str.contains("T", na=False)
    out[iso] = pd.to_datetime(s[iso], format="%Y-%m-%d").astype("datetime64[ns]")
    out[dmy] = pd.to_datetime(s[dmy], format="%d.%m.%Y").astype("datetime64[ns]")
    # offsets differ per row -> convert every value to UTC first, then take the calendar date
    local = pd.to_datetime(s[stamp].str[:10], format="%Y-%m-%d")
    out[stamp] = local.astype("datetime64[ns]")
    return out


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()

    # 1. one row per account: the most recently updated version wins
    df["_updated"] = pd.to_datetime(df["updated_at"], format="%Y-%m-%d %H:%M:%S")
    df = (df.sort_values(["account_id", "_updated"], kind="stable")
            .drop_duplicates("account_id", keep="last"))

    # 2. dates
    df["signup_date"] = parse_signup_date(df["signup_date"])

    # 3. categoricals: normalise, then map everything outside the known vocabulary to missing
    region = df["region"].fillna("").str.strip().str.upper()
    df["region"] = region.where(~region.isin(MISSING_REGION), None)
    tier = df["tier"].fillna("").str.strip().str.lower()
    df["tier"] = tier.where(tier.isin(VALID_TIERS), None)

    # 4. fee: strip the currency prefix; annual amounts become monthly
    fee = pd.to_numeric(df["fee"].str.replace("USD", "", regex=False).str.strip(), errors="coerce")
    annual = df["fee_unit"].str.strip().str.lower().eq("usd_year")
    df["monthly_fee_usd"] = np.where(annual, fee / 12.0, fee).round(2)

    # 5. employees: sentinel codes and impossible values are missing, not numbers
    emp = pd.to_numeric(df["employees"], errors="coerce")
    bad = emp.isin(EMPLOYEE_CODES) | (emp < EMPLOYEE_RANGE[0]) | (emp > EMPLOYEE_RANGE[1])
    df["employees"] = emp.mask(bad)

    return df[OUTPUT_COLUMNS].sort_values("account_id").reset_index(drop=True)


if __name__ == "__main__":
    out = clean(load_raw())
    print(out.head(10))
    print(out.dtypes)
    print(out.isna().sum())
