"""Behavioural checks for f1. They follow the specification in ../README.md only."""
from datetime import datetime

import pytest

LINES = [
    "P1,2025-06-01T08:00:00,ALA,2.5",
    "P1,2025-06-01T10:00:00,AST,2.5",
    "P2,2025-06-01T07:00:00,ALA,10",
    "P1,2025-06-02T09:00:00,SHY,2.5",
]


def fields(scan):
    return tuple(scan)[:4]


def sc(pid, ts, depot="ALA", kg=1.0):
    return (pid, datetime.fromisoformat(ts), depot, kg)


# ---------------------------------------------------------------- parse_scan
def test_parse_valid_line(rr):
    assert fields(rr.parse_scan("P004512,2025-06-02T08:15:00,ALA,3\n")) == (
        "P004512", datetime(2025, 6, 2, 8, 15), "ALA", 3)


def test_parse_fractional_weight(rr):
    scan = rr.parse_scan("P1,2025-06-01T08:00:00,ALA,2.75")
    assert scan is not None, "fractional weights are valid"
    assert fields(scan)[3] == pytest.approx(2.75)


@pytest.mark.parametrize("bad", ["", "garbage", "P1,not-a-date,ALA,2", "P1,2025-06-01T08:00:00,ALA,heavy",
                                 "P1,2025-06-01T08:00:00,ALA", "P1,2025-06-01T08:00:00,ALA,0",
                                 "P1,2025-06-01T08:00:00,ALA,-1.5", "P1,2025-06-01T08:00:00,,2",
                                 ",2025-06-01T08:00:00,ALA,2", "P1,2025-06-01T08:00:00,ALA,2,extra"])
def test_parse_malformed_returns_none(rr, bad):
    assert rr.parse_scan(bad) is None


# ---------------------------------------------------------------- load_scans
def test_load_skips_malformed_and_exact_duplicates(rr):
    assert len(rr.load_scans(LINES + [LINES[0], "garbage"])) == 4


def test_load_has_no_memory_between_calls(rr):
    first = rr.load_scans(list(LINES))
    second = rr.load_scans(list(LINES))
    assert len(first) == len(second) == 4


# ---------------------------------------------------------------- group_legs
def test_legs_split_on_idle_gap(rr):
    legs = rr.group_legs(rr.load_scans(LINES), max_idle_hours=12)
    assert {k: len(v) for k, v in legs.items()} == {"P1": 2, "P2": 1}
    first = legs["P1"][0]
    assert first["n_scans"] == 2 and list(first["depots"]) == ["ALA", "AST"]
    assert first["start"] == datetime(2025, 6, 1, 8) and first["end"] == datetime(2025, 6, 1, 10)


def test_gap_equal_to_threshold_stays_in_leg(rr):
    legs = rr.group_legs([sc("P1", "2025-06-01T08:00:00"), sc("P1", "2025-06-01T20:00:00")], max_idle_hours=12)
    assert len(legs["P1"]) == 1


def test_unsorted_input(rr):
    scans = [sc("P1", "2025-06-02T09:00:00", "SHY"), sc("P1", "2025-06-01T10:00:00", "AST"),
             sc("P1", "2025-06-01T08:00:00", "ALA")]
    legs = rr.group_legs(scans, max_idle_hours=12)["P1"]
    assert [list(x["depots"]) for x in legs] == [["ALA", "AST"], ["SHY"]]
    assert legs[0]["start"] < legs[1]["start"], "legs are returned in chronological order"


def test_gap_longer_than_a_day(rr):
    scans = [sc("P1", "2025-06-01T08:00:00"), sc("P1", "2025-06-02T08:30:00")]
    assert len(rr.group_legs(scans, max_idle_hours=12)["P1"]) == 2


def test_group_legs_does_not_mutate_input(rr):
    scans = [sc("P1", "2025-06-01T20:00:00"), sc("P1", "2025-06-01T08:00:00")]
    before = list(scans)
    rr.group_legs(scans)
    assert scans == before


# ---------------------------------------------------------------- trailing_average
def test_trailing_average_window(rr):
    assert rr.trailing_average([1, 2, 3, 4, 5], 3) == pytest.approx([1.0, 1.5, 2.0, 3.0, 4.0])


def test_trailing_average_window_one_and_empty(rr):
    assert rr.trailing_average([4, 8], 1) == pytest.approx([4.0, 8.0])
    assert rr.trailing_average([], 3) == []


def test_trailing_average_window_longer_than_data(rr):
    assert rr.trailing_average([2, 4], 10) == pytest.approx([2.0, 3.0])


# ---------------------------------------------------------------- busiest_depots
def test_busiest_depots_order_and_ties(rr):
    counts = {"SHY": 5, "ALA": 8, "AST": 5, "KRG": 1}
    assert [d for d, _ in rr.busiest_depots(counts, k=3)] == ["ALA", "AST", "SHY"]


def test_busiest_depots_k_larger_than_population(rr):
    assert len(rr.busiest_depots({"ALA": 1}, k=5)) == 1


# ---------------------------------------------------------------- build_report
def test_build_report_contract(rr):
    r = rr.build_report(LINES + ["garbage"], max_idle_hours=12, k=1)
    assert r["n_scans"] == 4 and r["n_parcels"] == 2
    assert r["n_legs"] == {"P1": 2, "P2": 1}
    assert r["transit_hours"] == pytest.approx({"P1": 2.0, "P2": 0.0})
    assert r["longest_leg_hours"] == pytest.approx({"P1": 2.0, "P2": 0.0})
    assert [d for d, _ in r["busiest_depots"]] == ["ALA"]


def test_build_report_long_leg_hours(rr):
    lines = ["P9,2025-06-01T08:00:00,ALA,1", "P9,2025-06-01T18:00:00,AST,1",
             "P9,2025-06-02T04:00:00,SHY,1", "P9,2025-06-02T14:00:00,KRG,1"]
    r = rr.build_report(lines, max_idle_hours=12)
    assert r["n_legs"] == {"P9": 1}
    assert r["longest_leg_hours"]["P9"] == pytest.approx(30.0), "a leg may last longer than a day"
    assert r["transit_hours"]["P9"] == pytest.approx(30.0)


def test_build_report_is_repeatable(rr):
    assert rr.build_report(list(LINES)) == rr.build_report(list(LINES))
