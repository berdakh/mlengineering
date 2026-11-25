"""Checks for the three SQL problems. Each query is run on the shipped SYNTHETIC database, on one
regenerated with another seed (so a hard-coded answer fails), and on tiny hand-built databases with the
trap the problem is about. Expected results come from an independent pandas oracle (oracle.py) or are
written out by hand for the tiny cases."""
from __future__ import annotations

import pytest

import oracle
from conftest import DB, run_sql, tiny_db

CITIES = [(1, "North"), (2, "South"), (3, "East")]
DRIVERS = [(1, 1, "2026-01-01"), (2, 1, "2026-01-01"), (3, 1, "2026-01-01"), (4, 2, "2026-01-01")]


def _q1_norm(rows):
    return sorted((r[0], int(r[1]), int(r[2]), round(float(r[3]), 2)) for r in rows)


# ---------------------------------------------------------------- Q1
@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_q1_matches_oracle(target, reseeded_db, which):
    db = DB if which == "shipped" else reseeded_db
    assert _q1_norm(run_sql(target, "q1_city_revenue", db)) == oracle.q1(db)


def test_q1_payment_attempts_do_not_fan_out(target, tmp_path):
    trips = [(1, 1, 1, "2026-03-05 10:00:00", "completed", 1000),
             (2, 1, 1, "2026-03-06 10:00:00", "completed", 2000),     # never paid
             (3, 4, 2, "2026-03-07 10:00:00", "cancelled_rider", None),
             (4, 1, 1, "2026-02-28 23:59:00", "completed", 9999),     # February
             (5, 1, 1, "2026-03-31 23:59:00", "completed", 500)]
    payments = [(1, 1, "2026-03-05 10:30:00", 1000, "failed"), (2, 1, "2026-03-05 10:35:00", 1000, "failed"),
                (3, 1, "2026-03-05 10:40:00", 1000, "succeeded"), (4, 2, "2026-03-06 10:30:00", 2000, "failed"),
                (5, 4, "2026-02-28 23:59:30", 9999, "succeeded"), (6, 5, "2026-04-01 00:30:00", 500, "succeeded")]
    db = tiny_db(tmp_path, CITIES, DRIVERS, trips, payments)
    got = _q1_norm(run_sql(target, "q1_city_revenue", db))
    assert got == [("East", 0, 0, 0.0), ("North", 3, 2, 15.0), ("South", 0, 0, 0.0)]


def test_q1_output_is_ordered_by_city(target):
    rows = run_sql(target, "q1_city_revenue", DB)
    assert len(rows) == 5, "one row per city, including cities with no trips"
    assert [r[0] for r in rows] == sorted(r[0] for r in rows)


# ---------------------------------------------------------------- Q2
@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_q2_matches_oracle(target, reseeded_db, which):
    db = DB if which == "shipped" else reseeded_db
    got = [(r[0], int(r[1]), int(r[2]), int(r[3])) for r in run_sql(target, "q2_top_drivers", db)]
    assert got == oracle.q2(db)


def test_q2_ties_give_exactly_two_rows(target, tmp_path):
    def trip(i, d, c, day, status="completed"):
        return (i, d, c, f"2026-03-{day:02d} 12:00:00", status, 100 if status == "completed" else None)
    trips = [trip(1, 1, 1, 1), trip(2, 1, 1, 2), trip(3, 2, 1, 3), trip(4, 2, 1, 4),
             trip(5, 3, 1, 5), trip(6, 3, 1, 6),                          # drivers 1, 2, 3 tie with 2 trips
             trip(7, 3, 1, 7, "cancelled_driver"), trip(8, 3, 1, 8, "cancelled_rider"),
             trip(9, 4, 2, 9)]
    db = tiny_db(tmp_path, CITIES, DRIVERS, trips)
    got = [(r[0], int(r[1]), int(r[2]), int(r[3])) for r in run_sql(target, "q2_top_drivers", db)]
    assert got == [("North", 1, 2, 1), ("North", 2, 2, 2), ("South", 4, 1, 1)]


# ---------------------------------------------------------------- Q3
@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_q3_matches_oracle(target, reseeded_db, which):
    db = DB if which == "shipped" else reseeded_db
    got = [(int(r[0]), str(r[1]), int(r[2])) for r in run_sql(target, "q3_longest_streak", db)]
    assert got == oracle.q3(db)


def test_q3_several_trips_a_day_and_ties(target, tmp_path):
    trips, i = [], 0
    def add(d, day, n=1, status="completed"):
        nonlocal i
        for h in range(n):
            i += 1
            trips.append((i, d, 1, f"{day} {10 + h:02d}:00:00", status, 100 if status == "completed" else None))
    for day in ("2026-03-01", "2026-03-02"):
        add(1, day, n=3)                    # 2-day streak with three trips a day
    for day in ("2026-03-10", "2026-03-11"):
        add(1, day)                         # another 2-day streak, later: the earlier one wins the tie
    add(1, "2026-03-03", status="cancelled_rider")   # a cancelled trip does not extend the streak
    add(2, "2026-03-31"); add(2, "2026-04-01"); add(2, "2026-04-02")   # across a month boundary
    db = tiny_db(tmp_path, CITIES, DRIVERS, trips)
    got = [(int(r[0]), str(r[1]), int(r[2])) for r in run_sql(target, "q3_longest_streak", db)]
    assert got == [(1, "2026-03-01", 2), (2, "2026-03-31", 3)]
