"""Generate the SYNTHETIC ride-hailing database for lesson w8d4 (SQL interview problems).

    python lessons/w8d4_coding_interviews/data/make_db.py                 # writes data/rides.db (seed 2026)
    python lessons/w8d4_coding_interviews/data/make_db.py --seed 7 --out /tmp/x.db
    python lessons/w8d4_coding_interviews/data/make_db.py --check         # regenerated tables == committed file

Invented data, built to contain the traps the problems test: several payment attempts per trip
(failed then succeeded), trips with no successful payment, cancelled trips with no fare, a city with no
trips in March 2026, drivers with several trips on one day, and ties in driver trip counts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sqlite3
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "rides.db"
CITIES = ["Almaty", "Astana", "Shymkent", "Aktobe", "Karaganda"]

SCHEMA = """
CREATE TABLE cities   (city_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
CREATE TABLE drivers  (driver_id INTEGER PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities,
                       joined_on TEXT NOT NULL);
CREATE TABLE riders   (rider_id INTEGER PRIMARY KEY, signup_date TEXT NOT NULL);
CREATE TABLE trips    (trip_id INTEGER PRIMARY KEY, driver_id INTEGER NOT NULL REFERENCES drivers,
                       rider_id INTEGER NOT NULL REFERENCES riders, city_id INTEGER NOT NULL REFERENCES cities,
                       requested_at TEXT NOT NULL, status TEXT NOT NULL, fare_cents INTEGER);
CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, trip_id INTEGER NOT NULL REFERENCES trips,
                       attempt_at TEXT NOT NULL, amount_cents INTEGER NOT NULL, status TEXT NOT NULL);
"""


def build(path: Path, seed: int) -> None:
    rng = np.random.default_rng(seed)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO cities VALUES (?, ?)", list(enumerate(CITIES, start=1)))

    start = dt.date(2026, 1, 1)
    n_drivers = 60
    drivers = []
    for d in range(1, n_drivers + 1):
        city = int(rng.integers(1, len(CITIES) + 1))
        joined = start + dt.timedelta(days=int(rng.integers(0, 75)))
        drivers.append((d, city, joined.isoformat()))
    # The last city gets no drivers active in March: move its drivers' joining to April.
    drivers = [(d, c, "2026-04-02" if c == len(CITIES) else j) for d, c, j in drivers]
    con.executemany("INSERT INTO drivers VALUES (?, ?, ?)", drivers)

    riders = [(r, (start + dt.timedelta(days=int(rng.integers(-200, 80)))).isoformat()) for r in range(1, 401)]
    con.executemany("INSERT INTO riders VALUES (?, ?)", riders)

    trips, payments = [], []
    trip_id = payment_id = 0
    end = dt.date(2026, 4, 30)
    for d, city, joined in drivers:
        day = dt.date.fromisoformat(joined)
        activity = rng.uniform(0.2, 0.9)       # share of days the driver works
        while day <= end:
            if rng.random() < activity:
                for _ in range(int(rng.integers(1, 5))):   # several trips per working day
                    trip_id += 1
                    t = dt.datetime.combine(day, dt.time(int(rng.integers(6, 23)), int(rng.integers(0, 60))))
                    u = rng.random()
                    status = "completed" if u < 0.82 else ("cancelled_rider" if u < 0.93 else "cancelled_driver")
                    fare = int(rng.integers(800, 6000)) if status == "completed" else None
                    trips.append((trip_id, d, int(rng.integers(1, 401)), city, t.isoformat(sep=" "), status, fare))
                    if status == "completed":
                        attempts = int(rng.choice([1, 1, 1, 2, 3]))
                        paid = rng.random() > 0.04            # 4 % never paid
                        for a in range(attempts):
                            payment_id += 1
                            last = a == attempts - 1
                            st = "succeeded" if (last and paid) else "failed"
                            at = t + dt.timedelta(minutes=30 + 5 * a)
                            payments.append((payment_id, trip_id, at.isoformat(sep=" "), fare, st))
            day += dt.timedelta(days=1)
    con.executemany("INSERT INTO trips VALUES (?, ?, ?, ?, ?, ?, ?)", trips)
    con.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?)", payments)
    con.commit()
    con.close()


def dump(path: Path) -> list:
    con = sqlite3.connect(path)
    out = [con.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
           for t in ("cities", "drivers", "riders", "trips", "payments")]
    con.close()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate the SYNTHETIC rides database.")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "rides.db"
            build(fresh, 2026)
            same = dump(fresh) == dump(DEFAULT_OUT)
        print("tables identical to the committed file" if same else "MISMATCH")
        return 0 if same else 1
    build(args.out, args.seed)
    con = sqlite3.connect(args.out)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("cities", "drivers", "riders", "trips", "payments")}
    print(f"wrote {args.out}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
