"""Build the SYNTHETIC cold-chain database used by lesson w2d2.

Six refrigeration units report temperature at irregular intervals. The data is simulated
so that the lab runs offline and so that specific traps (tied timestamps, re-sent rows,
outages, calibration changes, post-failure signal) are guaranteed to be present.
Nothing about real refrigeration equipment can be concluded from it.

    python lessons/w2d2_sql_windows_timeseries/data/make_db.py            # writes coldchain.db next to this file
    python lessons/w2d2_sql_windows_timeseries/data/make_db.py --check    # regenerate in memory, compare table contents

``build(path, seed)`` is also imported by the checks to create a second database
from a different seed, so that hard-coded answers do not pass.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

SEED = 2202
T0 = datetime(2026, 3, 1, tzinfo=timezone.utc)
DAYS = 3
T_END = T0 + timedelta(days=DAYS)          # report horizon: 2026-03-04 00:00:00
DEVICES = [("D01", "north"), ("D02", "north"), ("D03", "north"),
           ("D04", "south"), ("D05", "south"), ("D06", "south")]
STATUSES = ("running", "idle", "defrost", "fault")
ALERT_ABOVE_C = 8.0
OUT = Path(__file__).parent / "coldchain.db"

SCHEMA = """
CREATE TABLE devices (
    device_id TEXT PRIMARY KEY,
    site      TEXT NOT NULL
);
CREATE TABLE sensor_readings (
    reading_id  INTEGER PRIMARY KEY,      -- arrival order: a re-sent row has a HIGHER id
    device_id   TEXT    NOT NULL REFERENCES devices(device_id),
    ts          TEXT    NOT NULL,         -- 'YYYY-MM-DD HH:MM:SS' UTC, time of measurement
    ts_epoch    INTEGER NOT NULL,         -- the same instant as Unix seconds
    temperature REAL    NOT NULL,         -- degrees C as reported (before calibration)
    alert       INTEGER NOT NULL          -- 1 if the device firmware flagged the sample
);
CREATE TABLE device_status_events (
    event_id  INTEGER PRIMARY KEY,        -- log order: breaks ties between equal timestamps
    device_id TEXT    NOT NULL REFERENCES devices(device_id),
    ts        TEXT    NOT NULL,
    ts_epoch  INTEGER NOT NULL,
    status    TEXT    NOT NULL            -- running | idle | defrost | fault
);
CREATE TABLE calibration (
    device_id         TEXT    NOT NULL REFERENCES devices(device_id),
    valid_from        TEXT    NOT NULL,   -- the row applies from this instant (inclusive)
    valid_from_epoch  INTEGER NOT NULL,
    offset_c          REAL    NOT NULL,   -- add to the reported temperature
    alert_threshold_c REAL    NOT NULL,
    PRIMARY KEY (device_id, valid_from_epoch)
);
CREATE TABLE maintenance_labels (
    label_id       INTEGER PRIMARY KEY,
    device_id      TEXT    NOT NULL REFERENCES devices(device_id),
    label_ts       TEXT    NOT NULL,      -- inspection time = prediction time
    label_ts_epoch INTEGER NOT NULL,
    failed         INTEGER NOT NULL       -- 1 if the unit failed within the hour AFTER label_ts
);
CREATE INDEX idx_readings_device_ts ON sensor_readings (device_id, ts_epoch);
CREATE INDEX idx_status_device_ts ON device_status_events (device_id, ts_epoch);

-- One row per (device_id, ts): the row that arrived last wins.
CREATE VIEW readings_dedup AS
SELECT reading_id, device_id, ts, ts_epoch, temperature, alert
FROM (
    SELECT r.*,
           ROW_NUMBER() OVER (PARTITION BY device_id, ts_epoch ORDER BY reading_id DESC) AS rn
    FROM sensor_readings AS r
)
WHERE rn = 1;
"""


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M:%S")


def epoch(t: datetime) -> int:
    return int(t.timestamp())


def simulate(seed: int = SEED) -> dict[str, list[tuple]]:
    rng = random.Random(seed)
    readings: list[dict] = []          # measurement rows before ids are assigned
    resent: list[dict] = []
    status_rows: list[tuple] = []      # (device, datetime, status, order)
    calibration: list[tuple] = []
    labels: list[tuple] = []

    for d_index, (device, _site) in enumerate(DEVICES):
        # ---- labels: inspection times, some followed by a failure -------------------------
        n_labels = rng.randint(6, 7)
        slots = sorted(rng.sample(range(8, DAYS * 24 - 3, 3), n_labels))     # hours, >= 3 h apart
        dev_labels = []
        for hour in slots:
            when = T0 + timedelta(hours=hour, minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))
            dev_labels.append((when, int(rng.random() < 0.38)))
        if not any(f for _, f in dev_labels):
            dev_labels[-1] = (dev_labels[-1][0], 1)
        if all(f for _, f in dev_labels):
            dev_labels[0] = (dev_labels[0][0], 0)

        # ---- readings: ~5 min cadence with jitter, drops and outages ----------------------
        times: list[datetime] = []
        t = T0 + timedelta(seconds=rng.randint(0, 240))
        while t < T_END:
            if rng.random() > 0.04:                      # 4 % of samples are simply lost
                times.append(t)
            step = 300 + rng.randint(-60, 60)
            if rng.random() < 0.006:                     # occasional outage of 30-120 min
                step += rng.randint(30, 120) * 60
            t += timedelta(seconds=step)
        # exact boundary cases the checks rely on
        times.append(times[len(times) // 3] + timedelta(seconds=1800))       # a reading exactly 30 min later
        for when, _ in dev_labels[:2]:
            times.append(when)                                                # a reading exactly at label time
        times = sorted(set(x for x in times if x < T_END))

        # excursions: short warm episodes (door left open, compressor short-cycling)
        excursion = [0.0] * len(times)
        n_exc = rng.randint(7, 10)
        for _ in range(n_exc):
            start = rng.randrange(5, len(times) - 20)
            length = rng.randint(2, 12)
            height = rng.uniform(4.5, 8.0)
            for k in range(length):
                excursion[start + k] = max(excursion[start + k], height * math.sin(math.pi * (k + 1) / (length + 1)) + 2.5)
        # weak genuine precursor: a short warm episode in the 24 h before a failure
        for when, failed in dev_labels:
            if failed and rng.random() < 0.7:
                idx = [i for i, x in enumerate(times) if when - timedelta(hours=20) <= x < when - timedelta(hours=1)]
                if len(idx) > 6:
                    start = rng.choice(idx[:-5])
                    for k in range(rng.randint(2, 4)):
                        excursion[start + k] = max(excursion[start + k], rng.uniform(5.0, 6.5))

        noise = 0.0
        phase = rng.uniform(0, 2 * math.pi)
        base = 4.0 + rng.uniform(-0.6, 0.6)
        for i, when in enumerate(times):
            noise = 0.7 * noise + rng.gauss(0, 0.25)
            hours = (when - T0).total_seconds() / 3600
            temp = base + 0.8 * math.sin(2 * math.pi * hours / 24 + phase) + noise + excursion[i]
            # the consequence of a failure shows up only AFTER the label time
            for label_time, failed in dev_labels:
                if failed and label_time < when <= label_time + timedelta(minutes=60):
                    temp += 6.0 + rng.uniform(0, 1.5)
            alert = int(temp > ALERT_ABOVE_C)
            if rng.random() < 0.004:                     # isolated spurious flag
                alert = 1
            readings.append({"device": device, "t": when, "temp": round(temp, 2), "alert": alert})

        # re-sent rows: same device and timestamp, corrected value, arrives later
        own = [r for r in readings if r["device"] == device]
        quiet = [r for r in own if r["alert"] == 0]
        for r in rng.sample(own, k=max(8, len(own) // 50)):
            resent.append({"device": device, "t": r["t"], "temp": round(r["temp"] + rng.uniform(-0.4, 0.4), 2),
                           "alert": r["alert"]})
        # guaranteed trap: first copy not flagged, re-sent copy flagged
        for r in rng.sample(quiet, k=2):
            resent.append({"device": device, "t": r["t"], "temp": round(ALERT_ABOVE_C + rng.uniform(0.3, 1.5), 2),
                           "alert": 1})

        # ---- status events ------------------------------------------------------------------
        events: list[tuple[datetime, str]] = [(T0, "running")]
        t = T0
        while True:
            t += timedelta(minutes=rng.randint(120, 600))
            if t >= T_END - timedelta(hours=2):
                break
            events.append((t.replace(second=0), rng.choice(STATUSES[:3] if rng.random() < 0.85 else STATUSES)))
        for when, failed in dev_labels:
            if failed:
                fault_at = when + timedelta(minutes=rng.randint(5, 20), seconds=rng.randint(0, 59))
                events.append((fault_at, "fault"))
                events.append((fault_at + timedelta(minutes=rng.randint(60, 120)), "running"))
        events = sorted((e for e in events if e[0] < T_END), key=lambda e: e[0])
        cleaned: list[tuple[datetime, str]] = []
        for when, status in events:                      # no two consecutive events with the same status
            if cleaned and cleaned[-1][1] == status:
                continue
            cleaned.append((when, status))
        # guaranteed trap: the last two log lines share a timestamp; log order decides
        last_time, last_status = cleaned[-1]
        closing = rng.choice([s for s in STATUSES if s != last_status])
        cleaned.append((last_time, closing))
        # a second tie in the middle of the log
        mid = len(cleaned) // 2
        mid_time, mid_status = cleaned[mid]
        if cleaned[mid - 1][1] != "defrost" and mid_status != "defrost":
            cleaned.insert(mid, (mid_time, "defrost"))
        for order, (when, status) in enumerate(cleaned):
            status_rows.append((device, when, status, order))

        # ---- calibration: slowly changing ---------------------------------------------------
        first = T0 + timedelta(hours=6) if device == "D06" else T0 - timedelta(days=1)
        change_times = [first]
        for _ in range(rng.randint(1, 3)):
            change_times.append(T0 + timedelta(hours=rng.randint(8, DAYS * 24 - 6), minutes=rng.choice([0, 15, 30, 45])))
        if d_index == 0:                                   # a change exactly at a reading's timestamp
            change_times.append(times[len(times) // 2])
        for when in sorted(set(change_times)):
            calibration.append((device, iso(when), epoch(when), round(rng.uniform(-0.8, 0.8), 2),
                                round(rng.choice([7.5, 8.0, 8.5]), 1)))
        for when, failed in dev_labels:
            labels.append((device, when, failed))

    # ---- assign ids ---------------------------------------------------------------------------
    # first transmissions arrive in time order across devices; re-sent rows arrive afterwards
    readings.sort(key=lambda r: (r["t"], r["device"]))
    rng.shuffle(resent)
    reading_rows = [(i + 1, r["device"], iso(r["t"]), epoch(r["t"]), r["temp"], r["alert"])
                    for i, r in enumerate(readings + resent)]
    status_rows.sort(key=lambda e: (e[1], e[0], e[3]))
    # within one device, equal timestamps keep their log order because the sort is stable on `order`
    event_rows = [(i + 1, dev, iso(when), epoch(when), status) for i, (dev, when, status, _o) in enumerate(status_rows)]
    labels.sort(key=lambda x: (x[1], x[0]))
    label_rows = [(i + 1, dev, iso(when), epoch(when), failed) for i, (dev, when, failed) in enumerate(labels)]
    return {
        "devices": list(DEVICES),
        "sensor_readings": reading_rows,
        "device_status_events": event_rows,
        "calibration": calibration,
        "maintenance_labels": label_rows,
    }


def build(path: str | Path, seed: int = SEED) -> None:
    """Create the database at ``path`` (overwriting it) from ``seed``."""
    path = Path(path)
    if path.exists():
        path.unlink()
    tables = simulate(seed)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA)
        for name, rows in tables.items():
            marks = ",".join("?" * len(rows[0]))
            con.executemany(f"INSERT INTO {name} VALUES ({marks})", rows)
        con.commit()
        con.execute("VACUUM")
    finally:
        con.close()


def content_digest(path: str | Path) -> str:
    """Hash of table contents (not of the file, whose bytes depend on the SQLite version)."""
    con = sqlite3.connect(path)
    h = hashlib.sha256()
    try:
        for name in ("devices", "sensor_readings", "device_status_events", "calibration", "maintenance_labels"):
            for row in con.execute(f"SELECT * FROM {name} ORDER BY 1, 2"):
                h.update(repr(row).encode())
    finally:
        con.close()
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the synthetic cold-chain SQLite database.")
    ap.add_argument("--check", action="store_true", help="compare a fresh build with the committed file")
    args = ap.parse_args()
    if args.check:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "fresh.db"
            build(fresh)
            a, b = content_digest(fresh), content_digest(OUT)
        print("regenerated:", a)
        print("on disk:    ", b)
        raise SystemExit(0 if a == b else 1)
    build(OUT)
    con = sqlite3.connect(OUT)
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ("devices", "sensor_readings", "device_status_events", "calibration", "maintenance_labels")}
    con.close()
    print(f"wrote {OUT} ({OUT.stat().st_size / 1e3:.0f} kB) {counts}")
    print("content sha256:", content_digest(OUT)[:16])


if __name__ == "__main__":
    main()
