"""Checks for f3. Small hand-written frames pin down each rule; the full file is compared with the
generator's ground truth. Missing values may be None, NaN, NaT or pd.NA - all are accepted."""
import numpy as np
import pandas as pd
import pytest

COLUMNS = ["account_id", "signup_date", "region", "tier", "monthly_fee_usd", "employees"]


def row(**kw):
    base = {"account_id": "A1", "signup_date": "2024-03-05", "region": "ALA", "tier": "starter",
            "fee": "49.00", "fee_unit": "usd_month", "employees": "30", "updated_at": "2025-11-01 10:00:00"}
    base.update(kw)
    return base


def frame(*rows):
    return pd.DataFrame(list(rows), dtype=str)


def one(clean, **kw):
    out = clean(frame(row(**kw)))
    assert len(out) == 1
    return out.iloc[0]


# ----------------------------------------------------------------- contract
def test_output_columns_and_no_mutation(clean, raw):
    before = raw.copy()
    out = clean(raw)
    assert list(out.columns) == COLUMNS
    pd.testing.assert_frame_equal(raw, before)  # the caller's frame is untouched


def test_types(cleaned):
    assert pd.api.types.is_datetime64_any_dtype(cleaned["signup_date"])
    assert getattr(cleaned["signup_date"].dt, "tz", None) is None, "signup_date must be timezone-naive (UTC date)"
    assert pd.api.types.is_numeric_dtype(cleaned["monthly_fee_usd"])
    assert pd.api.types.is_numeric_dtype(cleaned["employees"])


# ----------------------------------------------------------------- duplicates
def test_exact_duplicates_removed(clean):
    assert len(clean(frame(row(), row()))) == 1


def test_latest_version_of_an_account_wins(clean):
    out = clean(frame(row(tier="enterprise", fee="399.00", updated_at="2025-11-20 09:00:00"),
                      row(tier="starter", updated_at="2025-06-01 09:00:00")))
    assert len(out) == 1 and out.iloc[0]["tier"] == "enterprise"
    assert out.iloc[0]["monthly_fee_usd"] == pytest.approx(399.0)


def test_one_row_per_account_on_full_file(cleaned, expected):
    assert cleaned["account_id"].is_unique
    assert len(cleaned) == len(expected)


# ----------------------------------------------------------------- dates
@pytest.mark.parametrize("text, date", [
    ("2024-03-05", "2024-03-05"),
    ("05.03.2024", "2024-03-05"),                    # DD.MM.YYYY, ambiguous with MM.DD
    ("25.12.2024", "2024-12-25"),
    ("2024-03-05T10:00:00+00:00", "2024-03-05"),
    ("2024-03-06T04:30:00+06:00", "2024-03-05"),     # 22:30 UTC on the 5th
    ("2024-03-04T21:00:00-07:00", "2024-03-05"),     # 04:00 UTC on the 5th
])
def test_signup_date_formats(clean, text, date):
    assert pd.Timestamp(one(clean, signup_date=text)["signup_date"]) == pd.Timestamp(date)


# ----------------------------------------------------------------- categoricals
@pytest.mark.parametrize("text", ["ALA", "ala", "ALA ", " Ala"])
def test_region_normalised(clean, text):
    assert one(clean, region=text)["region"] == "ALA"


@pytest.mark.parametrize("text", ["n/a", "?", None])
def test_region_missing_codes(clean, text):
    assert pd.isna(one(clean, region=text)["region"])


@pytest.mark.parametrize("text", ["enterprise", "ENTERPRISE", " enterprise", "Enterprise "])
def test_tier_normalised(clean, text):
    assert one(clean, tier=text, fee="399.00")["tier"] == "enterprise"


def test_unknown_tier_is_missing(clean):
    assert pd.isna(one(clean, tier="platinum")["tier"])


# ----------------------------------------------------------------- numerics
@pytest.mark.parametrize("fee, unit, usd", [("49.00", "usd_month", 49.0), ("USD 149.00", "usd_month", 149.0),
                                            ("4788.00", "usd_year", 399.0)])
def test_fee_monthly_usd(clean, fee, unit, usd):
    assert one(clean, fee=fee, fee_unit=unit)["monthly_fee_usd"] == pytest.approx(usd)


@pytest.mark.parametrize("text", ["-1", "99999", "0", "250000", "-40"])
def test_employees_codes_and_impossible_values(clean, text):
    assert pd.isna(one(clean, employees=text)["employees"])


@pytest.mark.parametrize("text, value", [("1", 1), ("42", 42), ("50000", 50000)])
def test_valid_employees_kept(clean, text, value):
    assert one(clean, employees=text)["employees"] == value


# ----------------------------------------------------------------- full file vs ground truth
def test_full_file_matches_ground_truth(cleaned, expected):
    exp = expected.sort_values("account_id").reset_index(drop=True)
    assert list(cleaned["account_id"]) == list(exp["account_id"])
    problems = {}
    same_date = pd.to_datetime(cleaned["signup_date"]).values == exp["signup_date"].values
    problems["signup_date"] = int((~same_date).sum())
    for col in ("region", "tier"):
        got, want = cleaned[col], exp[col]
        ok = (got.isna() & want.isna()) | (got.astype(object) == want.astype(object))
        problems[col] = int((~ok.fillna(False).astype(bool)).sum())
    for col in ("monthly_fee_usd", "employees"):
        got = pd.to_numeric(cleaned[col], errors="coerce").astype(float).to_numpy()
        want = exp[col].astype(float).to_numpy()
        problems[col] = int((~np.isclose(got, want, equal_nan=True, atol=0.005)).sum())
    wrong = {k: v for k, v in problems.items() if v}
    assert not wrong, f"rows differing from ground truth, per column: {wrong}"
