"""Planned drift annotated, unplanned drift and missingness detected, few false alarms (8 seeds)."""
from __future__ import annotations

import pandas as pd
import pytest

from conftest import SEEDS

EV = {"planned": 30, "length_bug": 42, "price_bug": 50, "missing": 56}


def _has(df, feature, kind, lo, hi):
    return bool(((df["feature"] == feature) & (df["kind"] == kind) & df["day"].between(lo, hi)).any())


def test_alert_format(alerts_by_seed):
    for seed, df in alerts_by_seed.items():
        assert set(df["kind"]) <= {"unexpected", "expected", "missing"}, f"seed {seed}: kinds {set(df['kind'])}"
        assert df["day"].map(lambda d: isinstance(d, int) or float(d).is_integer()).all()


@pytest.mark.parametrize("seed", SEEDS)
def test_planned_change_is_annotated_not_alerted(alerts_by_seed, seed):
    df = alerts_by_seed[seed]
    assert _has(df, "price", "expected", EV["planned"], EV["planned"] + 2), \
        "the planned price change should be visible as an 'expected' annotation within 3 days"
    early = df[(df["feature"] == "price") & (df["kind"] == "unexpected") & df["day"].between(30, 36)]
    assert early.empty, f"seed {seed}: planned change alerted as unexpected on days {list(early['day'])}"


@pytest.mark.parametrize("seed", SEEDS)
def test_unplanned_changes_are_detected_quickly(alerts_by_seed, seed):
    df = alerts_by_seed[seed]
    assert _has(df, "session_length_s", "unexpected", 42, 44), f"seed {seed}: session-length bug not caught by day 44"
    assert _has(df, "price", "unexpected", 50, 52), \
        f"seed {seed}: the unplanned price drop on day 50 was not caught by day 52 (suppression must end)"
    assert _has(df, "basket_size", "missing", 56, 57), f"seed {seed}: basket_size missingness not caught by day 57"


@pytest.mark.parametrize("seed", SEEDS)
def test_few_false_alarms(alerts_by_seed, seed):
    df = alerts_by_seed[seed]
    unexpected = df[df["kind"] == "unexpected"]
    true_drift = (((unexpected["feature"] == "session_length_s") & (unexpected["day"] >= 42))
                  | ((unexpected["feature"] == "price") & (unexpected["day"] >= 50)))
    false = unexpected[~true_drift]
    assert len(false) <= 4, f"seed {seed}: {len(false)} unexpected alerts on stable feature-days: {false.values.tolist()}"
    wrong_missing = df[(df["kind"] == "missing") & ~((df["feature"] == "basket_size") & df["day"].between(56, 59))]
    assert wrong_missing.empty, f"seed {seed}: missingness alerts where nothing is missing: {wrong_missing.values.tolist()}"


def test_deterministic(monitor, calendar):
    import make_stream
    df = make_stream.generate(3)
    assert monitor.monitor_stream(df, calendar) == monitor.monitor_stream(df, calendar)
