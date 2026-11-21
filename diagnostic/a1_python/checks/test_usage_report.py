"""Behavioural checks for a1. They follow the specification in ../README.md only."""
from datetime import datetime

import pytest

LINES = [
    "C1,2025-03-01T10:00:00,10",
    "C1,2025-03-01T10:20:00,5.5",
    "C2,2025-03-01T09:00:00,30",
    "C1,2025-03-01T12:00:00,20",
]


def fields(event):
    return tuple(event)[:3]


# ---------------------------------------------------------------- parse_line
def test_parse_valid_line(ur):
    cid, ts, minutes = fields(ur.parse_line("C00017,2025-03-02T21:15:00,42\n"))
    assert (cid, ts, minutes) == ("C00017", datetime(2025, 3, 2, 21, 15), 42)


def test_parse_fractional_minutes(ur):
    event = ur.parse_line("C1,2025-03-01T10:20:00,5.5")
    assert event is not None, "fractional minutes are valid"
    assert fields(event)[2] == pytest.approx(5.5)


@pytest.mark.parametrize("bad", ["", "garbage", "C1,not-a-date,5", "C1,2025-03-01T10:00:00,abc",
                                 "C1,2025-03-01T10:00:00", "C1,2025-03-01T10:00:00,-3"])
def test_parse_malformed_returns_none(ur, bad):
    assert ur.parse_line(bad) is None


# ---------------------------------------------------------------- load_events
def test_load_skips_malformed_and_exact_duplicates(ur):
    events = ur.load_events(LINES + [LINES[0], "garbage"])
    assert len(events) == 4


def test_load_has_no_memory_between_calls(ur):
    first = ur.load_events(list(LINES))
    second = ur.load_events(list(LINES))
    assert len(first) == len(second) == 4


# ---------------------------------------------------------------- sessionize
def ev(cid, ts, minutes=1.0):
    return (cid, datetime.fromisoformat(ts), minutes)


def test_sessions_split_on_gap(ur):
    s = ur.sessionize(ur.load_events(LINES), gap_minutes=30)
    assert {k: len(v) for k, v in s.items()} == {"C1": 2, "C2": 1}
    first = s["C1"][0]
    assert first["minutes"] == pytest.approx(15.5) and first["n_events"] == 2
    assert first["start"] == datetime(2025, 3, 1, 10, 0) and first["end"] == datetime(2025, 3, 1, 10, 20)


def test_gap_equal_to_threshold_stays_in_session(ur):
    s = ur.sessionize([ev("C1", "2025-03-01T10:00:00"), ev("C1", "2025-03-01T10:30:00")], gap_minutes=30)
    assert len(s["C1"]) == 1


def test_unsorted_input(ur):
    events = [ev("C1", "2025-03-01T12:00:00", 20), ev("C1", "2025-03-01T10:20:00", 5), ev("C1", "2025-03-01T10:00:00", 10)]
    s = ur.sessionize(events, gap_minutes=30)["C1"]
    assert [x["minutes"] for x in s] == [15, 20]
    assert s[0]["start"] < s[1]["start"], "sessions are returned in chronological order"


def test_gap_longer_than_a_day(ur):
    events = [ev("C1", "2025-03-01T10:00:00"), ev("C1", "2025-03-02T10:05:00")]
    assert len(ur.sessionize(events, gap_minutes=30)["C1"]) == 2


def test_sessionize_does_not_mutate_input(ur):
    events = [ev("C1", "2025-03-01T12:00:00"), ev("C1", "2025-03-01T10:00:00")]
    before = list(events)
    ur.sessionize(events)
    assert events == before


# ---------------------------------------------------------------- rolling_mean
def test_rolling_mean_trailing_window(ur):
    assert ur.rolling_mean([1, 2, 3, 4, 5], 3) == pytest.approx([1.0, 1.5, 2.0, 3.0, 4.0])


def test_rolling_mean_window_one_and_empty(ur):
    assert ur.rolling_mean([4, 8], 1) == pytest.approx([4.0, 8.0])
    assert ur.rolling_mean([], 3) == []


def test_rolling_mean_window_longer_than_data(ur):
    assert ur.rolling_mean([2, 4], 10) == pytest.approx([2.0, 3.0])


# ---------------------------------------------------------------- top_customers
def test_top_customers_order_and_ties(ur):
    totals = {"C3": 50.0, "C1": 80.0, "C2": 50.0, "C4": 10.0}
    assert [c for c, _ in ur.top_customers(totals, k=3)] == ["C1", "C2", "C3"]


def test_top_customers_k_larger_than_population(ur):
    assert len(ur.top_customers({"C1": 1.0}, k=5)) == 1


# ---------------------------------------------------------------- build_report
def test_build_report_contract(ur):
    r = ur.build_report(LINES + ["garbage"], gap_minutes=30, k=1)
    assert r["n_events"] == 4 and r["n_customers"] == 2
    assert r["total_minutes"] == pytest.approx({"C1": 35.5, "C2": 30})
    assert r["n_sessions"] == {"C1": 2, "C2": 1}
    assert r["longest_session_minutes"] == pytest.approx({"C1": 20, "C2": 30})
    assert [c for c, _ in r["top_customers"]] == ["C1"]


def test_build_report_is_repeatable(ur):
    assert ur.build_report(list(LINES)) == ur.build_report(list(LINES))
