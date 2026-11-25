"""The orders contract, graded by planted defects: each must be found and attributed to the right row."""
from __future__ import annotations

import pandas as pd
import pytest

import synth_orders as so
from conftest import failed


def describe(results):
    return "; ".join(f"[{r.severity}] {r.name}: {r.detail}" for r in results)


def test_clean_export_passes(run_checks):
    results = run_checks(so.clean_orders())
    assert len(results) >= 7, "expected at least one result per contract rule"
    for r in results:
        assert r.severity in ("error", "warning") and isinstance(r.detail, str) and r.name
    assert not failed(results), "the clean export must pass: " + describe(failed(results))


@pytest.mark.parametrize("defect", sorted(so.ROW_DEFECTS))
def test_row_level_violation_is_found_and_attributed(run_checks, defect):
    bad = failed(run_checks(so.with_row(so.clean_orders(), **so.ROW_DEFECTS[defect])))
    errors = [r for r in bad if r.severity == "error"]
    assert errors, f"'{defect}' violates the contract but no error-severity check failed"
    assert any(so.PLANTED in r.detail for r in errors), \
        f"'{defect}': no failing detail names the offending order {so.PLANTED}: {describe(bad)}"
    assert not any(so.SENTINEL in r.detail for r in bad), f"clean order {so.SENTINEL} was blamed: {describe(bad)}"


def test_duplicate_order_id(run_checks):
    bad = failed(run_checks(so.duplicate_order(so.clean_orders())))
    assert any(r.severity == "error" and so.PLANTED in r.detail for r in bad), describe(bad)


def test_guest_share_is_a_warning_not_an_error(run_checks):
    assert not failed(run_checks(so.many_guests(so.clean_orders(), 0.03))), "3 % guests is inside the contract"
    bad = failed(run_checks(so.many_guests(so.clean_orders(), 0.10)))
    assert bad and all(r.severity == "warning" for r in bad), \
        "10 % guest checkouts is suspicious, not invalid: exactly a warning. Got: " + describe(bad)


def test_a_day_without_orders_is_a_warning(run_checks):
    bad = failed(run_checks(so.lost_day(so.clean_orders())))
    assert bad and all(r.severity == "warning" for r in bad), describe(bad)
    assert any("2025-09-12" in r.detail for r in bad), "say which day is missing"


def test_all_violations_are_reported_together(run_checks):
    """Four different rules broken in four different rows: the report must name all four rows."""
    df = so.with_row(so.clean_orders(), amount="-40.00")
    planted = {so.PLANTED: None, so.SENTINEL: ("currency", "usd"),
               "ORD-100020": ("status", "returned"), "ORD-100030": ("order_ts", "30/09/2025")}
    for order_id, change in planted.items():
        if change:
            df.loc[df.index[df["order_id"] == order_id][0], change[0]] = change[1]
    text = describe(failed(run_checks(df)))
    missing = [order_id for order_id in planted if order_id not in text]
    assert not missing, f"not reported: {missing}. Evaluate every rule; do not stop at the first failure"


def test_missing_column_is_reported_not_raised(run_checks):
    results = run_checks(so.clean_orders().drop(columns=["refunded_amount"]))
    assert any(not r.passed and r.severity == "error" and "refunded_amount" in r.detail for r in results)


def test_garbage_never_raises(run_checks):
    df = so.clean_orders()
    df.loc[0, ["amount", "refunded_amount", "order_ts", "delivered_ts", "status", "currency"]] = \
        ["abc", "NaN", "", "yesterday", "", ""]
    assert failed(run_checks(df))
    run_checks(df.iloc[0:0])            # an empty export must not crash the checker either


def test_input_is_not_modified(run_checks):
    df = so.with_row(so.clean_orders(), amount="40,00")
    before = df.copy(deep=True)
    run_checks(df)
    pd.testing.assert_frame_equal(df, before)
