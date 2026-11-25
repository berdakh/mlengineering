"""Checks for the 45-minute mock: C1 (monotonic-deque window) and C2 (cohort with a relative window)."""
from __future__ import annotations

import random
import signal
import sqlite3
import time

import pandas as pd
import pytest

from conftest import DB, run_c2, tiny_db

LIMIT_S = 4.0


def _brute_c1(values, tol):
    best = (0, 0)
    for i in range(len(values)):
        for j in range(i, len(values)):
            window = values[i:j + 1]
            if max(window) - min(window) <= tol and j - i + 1 > best[1]:
                best = (i, j - i + 1)
    return best


def test_c1_known_answers(c1):
    assert c1([1, 3, 2, 2.5, 8, 8.2, 8.1, 8.3, 1], 1) == (4, 4)
    assert c1([], 1) == (0, 0)
    assert c1([5], 0) == (0, 1)
    assert c1([1, 2, 1, 2, 1, 2], 1) == (0, 6)       # adjacent steps of 1 and the range is 1
    assert c1([0, 1, 2, 3, 4], 1) == (0, 2)           # adjacent differences are small but the range grows
    assert c1([3, 3, 9, 9], 0) == (0, 2)              # ties: earliest run wins


def test_c1_matches_brute_force(c1):
    rng = random.Random(21)
    for _ in range(300):
        values = [rng.randint(0, 6) for _ in range(rng.randint(0, 25))]
        tol = rng.randint(0, 3)
        assert c1(values, tol) == _brute_c1(values, tol)


def test_c1_is_linear(c1):
    rng = random.Random(22)
    values = [rng.random() + (i // 5000) * 10 for i in range(300_000)]   # 60 blocks of 5,000 stable values

    def _raise(signum, frame):
        raise TimeoutError(f"longer than {LIMIT_S} s on 300,000 values: an O(n^2) scan?")
    old = signal.signal(signal.SIGALRM, _raise)
    signal.setitimer(signal.ITIMER_REAL, LIMIT_S)
    try:
        start, length = c1(values, 6.0)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    assert (start, length) == (0, 5000)


def _oracle_c2(db):
    con = sqlite3.connect(db)
    trips = pd.read_sql_query("SELECT * FROM trips WHERE status = 'completed'", con)
    drivers = pd.read_sql_query("SELECT * FROM drivers", con)
    cities = pd.read_sql_query("SELECT * FROM cities", con)
    con.close()
    trips["ts"] = pd.to_datetime(trips["requested_at"])
    rows = {}
    for driver, g in trips.groupby("driver_id"):
        first = g["ts"].min()
        if not (pd.Timestamp("2026-03-01") <= first < pd.Timestamp("2026-04-01")):
            continue
        n = int(((g["ts"] >= first) & (g["ts"] < first + pd.Timedelta(days=30))).sum())
        city = cities.set_index("city_id").loc[drivers.set_index("driver_id").loc[driver, "city_id"], "name"]
        size, active = rows.get(city, (0, 0))
        rows[city] = (size + 1, active + (n >= 25))
    return sorted((c, s, a, round(a / s, 3)) for c, (s, a) in rows.items())


@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_c2_matches_oracle(target, reseeded_db, which):
    db = DB if which == "shipped" else reseeded_db
    assert run_c2(target, db) == _oracle_c2(db)


def test_c2_window_is_relative_and_completed_only(target, tmp_path):
    drivers = [(1, 1, "2026-01-01"), (2, 1, "2026-03-01"), (3, 2, "2026-02-20"), (4, 2, "2026-02-01")]
    trips, i = [], 0

    def add(d, ts, status="completed"):
        nonlocal i
        i += 1
        trips.append((i, d, 1, ts, status, 100 if status == "completed" else None))
    # Driver 1: first completed trip 2026-03-20; 25 trips within 30 days, most of them in April
    # (a calendar-month count would see only 5).
    for k in range(25):
        add(1, f"2026-03-{20 + k:02d} 12:00:00" if k < 5 else f"2026-04-{(k - 5) % 18 + 1:02d} 12:00:00")
    # Driver 2: 30 trips, but 6 fall after the 30-day window -> 24 -> not active.
    for k in range(24):
        add(2, f"2026-03-{(k % 28) + 1:02d} 12:00:00")
    for k in range(6):
        add(2, "2026-04-15 12:00:00")
    # Driver 3: a cancelled trip in February does not make February the first trip; joined_on is irrelevant.
    add(3, "2026-02-25 09:00:00", status="cancelled_rider")
    add(3, "2026-03-02 09:00:00")
    # Driver 4: first completed trip in February -> not in the March cohort.
    add(4, "2026-02-27 09:00:00")
    add(4, "2026-03-05 09:00:00")
    db = tiny_db(tmp_path, drivers, trips)
    assert run_c2(target, db) == [("North", 2, 1, 0.5), ("South", 1, 0, 0.0)]
