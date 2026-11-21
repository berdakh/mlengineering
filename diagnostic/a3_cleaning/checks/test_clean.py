"""Checks for a3. Small hand-written frames pin down each rule; the full file is compared with the
generator's ground truth. Missing values may be None, NaN, NaT or pd.NA - all are accepted."""
import numpy as np
import pandas as pd
import pytest

COLUMNS = ["customer_id", "signup_date", "country", "plan", "monthly_price_usd", "age"]


def row(**kw):
    base = {"customer_id": "C1", "signup_date": "2024-03-05", "country": "US", "plan": "basic",
            "monthly_price": "9.99", "price_unit": "usd", "age": "30", "updated_at": "2025-11-01 10:00:00"}
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
    assert pd.api.types.is_numeric_dtype(cleaned["monthly_price_usd"])
    assert pd.api.types.is_numeric_dtype(cleaned["age"])


# ----------------------------------------------------------------- duplicates
def test_exact_duplicates_removed(clean):
    assert len(clean(frame(row(), row()))) == 1


def test_latest_version_of_a_customer_wins(clean):
    out = clean(frame(row(plan="premium", monthly_price="19.99", updated_at="2025-11-20 09:00:00"),
                      row(plan="basic", updated_at="2025-06-01 09:00:00")))
    assert len(out) == 1 and out.iloc[0]["plan"] == "premium"
    assert out.iloc[0]["monthly_price_usd"] == pytest.approx(19.99)


def test_one_row_per_customer_on_full_file(cleaned, expected):
    assert cleaned["customer_id"].is_unique
    assert len(cleaned) == len(expected)


# ----------------------------------------------------------------- dates
@pytest.mark.parametrize("text, date", [
    ("2024-03-05", "2024-03-05"),
    ("05/03/2024", "2024-03-05"),                    # DD/MM/YYYY, ambiguous with MM/DD
    ("25/12/2024", "2024-12-25"),
    ("2024-03-05T10:00:00+00:00", "2024-03-05"),
    ("2024-03-06T03:30:00+05:00", "2024-03-05"),     # 22:30 UTC on the 5th
    ("2024-03-04T20:00:00-08:00", "2024-03-05"),     # 04:00 UTC on the 5th
])
def test_signup_date_formats(clean, text, date):
    assert pd.Timestamp(one(clean, signup_date=text)["signup_date"]) == pd.Timestamp(date)


# ----------------------------------------------------------------- categoricals
@pytest.mark.parametrize("text", ["US", "us", " US", "Us "])
def test_country_normalised(clean, text):
    assert one(clean, country=text)["country"] == "US"


@pytest.mark.parametrize("text", ["unknown", "-", None])
def test_country_missing_codes(clean, text):
    assert pd.isna(one(clean, country=text)["country"])


@pytest.mark.parametrize("text", ["premium", "Premium", " premium ", "PREMIUM"])
def test_plan_normalised(clean, text):
    assert one(clean, plan=text)["plan"] == "premium"


def test_unknown_plan_is_missing(clean):
    assert pd.isna(one(clean, plan="gold")["plan"])


# ----------------------------------------------------------------- numerics
@pytest.mark.parametrize("price, unit, usd", [("9.99", "usd", 9.99), ("$14.99", "usd", 14.99), ("1999", "cents", 19.99)])
def test_price_in_usd(clean, price, unit, usd):
    assert one(clean, monthly_price=price, price_unit=unit)["monthly_price_usd"] == pytest.approx(usd)


@pytest.mark.parametrize("text", ["-1", "999", "0", "12", "150"])
def test_age_missing_codes_and_impossible_values(clean, text):
    assert pd.isna(one(clean, age=text)["age"])


@pytest.mark.parametrize("text, value", [("13", 13), ("42", 42), ("110", 110)])
def test_valid_age_kept(clean, text, value):
    assert one(clean, age=text)["age"] == value


# ----------------------------------------------------------------- full file vs ground truth
def test_full_file_matches_ground_truth(cleaned, expected):
    exp = expected.sort_values("customer_id").reset_index(drop=True)
    assert list(cleaned["customer_id"]) == list(exp["customer_id"])
    problems = {}
    same_date = pd.to_datetime(cleaned["signup_date"]).values == exp["signup_date"].values
    problems["signup_date"] = int((~same_date).sum())
    for col in ("country", "plan"):
        got, want = cleaned[col], exp[col]
        ok = (got.isna() & want.isna()) | (got.astype(object) == want.astype(object))
        problems[col] = int((~ok.fillna(False).astype(bool)).sum())
    for col in ("monthly_price_usd", "age"):
        got = pd.to_numeric(cleaned[col], errors="coerce").astype(float).to_numpy()
        want = exp[col].astype(float).to_numpy()
        problems[col] = int((~np.isclose(got, want, equal_nan=True, atol=0.005)).sum())
    wrong = {k: v for k, v in problems.items() if v}
    assert not wrong, f"rows differing from ground truth, per column: {wrong}"
