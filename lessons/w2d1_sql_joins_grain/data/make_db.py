"""Generate the SYNTHETIC maintenance database used by lesson w2d1 (and reused by w2d2).

"Northfield Pumps" is an invented equipment-maintenance business. Every row is simulated.
The database exists to practise query correctness; nothing about real maintenance
operations can be concluded from it. Schema: see data/README.md next to this file.

    python lessons/w2d1_sql_joins_grain/data/make_db.py            # writes maintenance.db here
    python lessons/w2d1_sql_joins_grain/data/make_db.py --check    # regenerate and compare contents

`build(path, seed)` is also imported by the checks, which grade queries on a second
database built from a different seed, so that hard-coded answers do not pass.

The traps this lesson is about are guaranteed for every seed:
  * a site with no machines, and a site with machines but no corrective orders in 2025
  * machines with no work orders, and machines with several work orders AND several downtime events
  * work orders with no parts, with one part line, and with several part lines
  * NULLs in work_orders.tech_id, work_orders.labor_hours, work_orders.closed_date,
    machines.criticality, machines.decommissioned_date, technicians.site_id, downtime_events.cause
  * technicians who were never assigned a work order; parts never used at all and
    parts used only on preventive orders
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import sqlite3
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "maintenance.db"
DEFAULT_SEED = 20261122

SCHEMA = """
CREATE TABLE sites (
    site_id      INTEGER PRIMARY KEY,
    site_name    TEXT NOT NULL,
    region       TEXT NOT NULL
);
CREATE TABLE machines (
    machine_id          INTEGER PRIMARY KEY,
    site_id             INTEGER NOT NULL REFERENCES sites(site_id),
    model               TEXT NOT NULL,
    installed_date      TEXT NOT NULL,
    decommissioned_date TEXT,              -- NULL = still in service
    criticality         TEXT               -- 'low' | 'medium' | 'high'; NULL = never assessed
);
CREATE TABLE technicians (
    tech_id   INTEGER PRIMARY KEY,
    tech_name TEXT NOT NULL,
    site_id   INTEGER REFERENCES sites(site_id)   -- NULL = external contractor
);
CREATE TABLE work_orders (
    wo_id       INTEGER PRIMARY KEY,
    machine_id  INTEGER NOT NULL REFERENCES machines(machine_id),
    wo_type     TEXT NOT NULL,             -- 'preventive' | 'corrective' | 'inspection'
    opened_date TEXT NOT NULL,
    closed_date TEXT,                      -- NULL = still open
    tech_id     INTEGER REFERENCES technicians(tech_id),  -- NULL = not assigned
    labor_hours REAL                       -- NULL = not recorded (not the same as 0)
);
CREATE TABLE parts (
    part_id   INTEGER PRIMARY KEY,
    part_name TEXT NOT NULL,
    unit_cost REAL NOT NULL
);
CREATE TABLE parts_used (
    wo_id    INTEGER NOT NULL REFERENCES work_orders(wo_id),
    part_id  INTEGER NOT NULL REFERENCES parts(part_id),
    quantity INTEGER NOT NULL,
    PRIMARY KEY (wo_id, part_id)
);
CREATE TABLE downtime_events (
    event_id   INTEGER PRIMARY KEY,
    machine_id INTEGER NOT NULL REFERENCES machines(machine_id),
    start_date TEXT NOT NULL,
    hours      REAL NOT NULL,
    cause      TEXT                        -- NULL = cause not determined
);
"""

SITE_NAMES = ["Aldermoor", "Brackwell", "Cinder Quay", "Dunmere", "Eastholt", "Fenwick Yard"]
REGIONS = ["north", "north", "coast", "south", "south", "coast"]
MODELS = ["CP-200", "CP-350", "VX-12", "VX-40", "HM-7"]
PART_NAMES = ["bearing kit", "mechanical seal", "impeller", "coupling insert", "gasket set",
              "drive belt", "pressure sensor", "motor capacitor", "shaft sleeve", "oil filter",
              "vibration mount", "inspection tag"]
CAUSES = ["bearing", "seal leak", "electrical", "cavitation", "operator"]
TECH_NAMES = ["Abe", "Bruna", "Chidi", "Dagny", "Emre", "Farah", "Goran", "Hana", "Ines", "Jomo",
              "Kalle", "Lucia"]


def _date(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    return start + dt.timedelta(days=rng.randrange((end - start).days + 1))


def build(path: str | Path, seed: int = DEFAULT_SEED) -> None:
    """Create the database at ``path`` (overwriting it)."""
    rng = random.Random(seed)
    path = Path(path)
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)

    n_sites = len(SITE_NAMES)
    con.executemany("INSERT INTO sites VALUES (?, ?, ?)",
                    [(i + 1, SITE_NAMES[i], REGIONS[i]) for i in range(n_sites)])
    empty_site = n_sites                      # last site: no machines at all
    quiet_site = n_sites - 1                  # has machines, but no corrective orders in 2025

    # ---- machines
    machines = []
    mid = 0
    for site in range(1, n_sites):            # every site except the empty one
        for _ in range(rng.randint(5, 9)):
            mid += 1
            installed = _date(rng, dt.date(2019, 1, 1), dt.date(2023, 12, 31))
            decommissioned = (_date(rng, dt.date(2025, 3, 1), dt.date(2025, 11, 30))
                              if rng.random() < 0.15 else None)
            criticality = rng.choice(["low", "medium", "high", None])
            machines.append([mid, site, rng.choice(MODELS), installed.isoformat(),
                             decommissioned.isoformat() if decommissioned else None, criticality])
    machines[0][4], machines[1][4] = None, "2025-06-30"     # guarantee both states exist
    machines[2][5], machines[3][5] = None, "high"
    con.executemany("INSERT INTO machines VALUES (?, ?, ?, ?, ?, ?)", machines)

    # ---- technicians (the last three are never assigned; two contractors have NULL site)
    techs = []
    for i, name in enumerate(TECH_NAMES, start=1):
        site = None if i in (4, 11) else rng.randint(1, n_sites - 1)
        techs.append((i, name, site))
    con.executemany("INSERT INTO technicians VALUES (?, ?, ?)", techs)
    assignable = [t[0] for t in techs[:-3]]

    # ---- parts (part 11 only ever used on preventive orders, part 12 never used)
    parts = [(i, name, round(rng.uniform(8, 420), 2)) for i, name in enumerate(PART_NAMES, start=1)]
    con.executemany("INSERT INTO parts VALUES (?, ?, ?)", parts)
    general_parts = [p[0] for p in parts[:10]]

    # ---- work orders
    by_site: dict[int, list[int]] = {}
    for m in machines:
        by_site.setdefault(m[1], []).append(m[0])
    no_wo_machines = {ids[-1] for ids in by_site.values()}          # one per site has none
    busy_machines = {ids[0] for ids in by_site.values()}            # guaranteed several of each
    work_orders, parts_used = [], []
    wo_id = 0
    for m in machines:
        machine_id, site = m[0], m[1]
        if machine_id in no_wo_machines:
            continue
        n = rng.randint(4, 7) if machine_id in busy_machines else rng.randint(1, 6)
        for _ in range(n):
            wo_id += 1
            wo_type = rng.choices(["preventive", "corrective", "inspection"], [0.4, 0.4, 0.2])[0]
            opened = _date(rng, dt.date(2024, 1, 1), dt.date(2025, 12, 20))
            if site == quiet_site and wo_type == "corrective" and opened.year == 2025:
                opened = opened.replace(year=2024)
            closed = None if rng.random() < 0.12 else opened + dt.timedelta(days=rng.randint(0, 14))
            tech = None if rng.random() < 0.15 else rng.choice(assignable)
            labor = None if rng.random() < 0.12 else round(rng.uniform(0.5, 16.0), 1)
            work_orders.append([wo_id, machine_id, wo_type, opened.isoformat(),
                                closed.isoformat() if closed else None, tech, labor])
            if wo_type == "inspection":
                n_parts = 0
            else:
                n_parts = rng.choices([0, 1, 2, 3, 4], [0.25, 0.25, 0.25, 0.15, 0.10])[0]
            for part_id in rng.sample(general_parts, n_parts):
                parts_used.append((wo_id, part_id, rng.randint(1, 4)))
    # guarantees that do not depend on the random draws
    work_orders[0][5], work_orders[0][6], work_orders[0][4] = None, None, None
    work_orders[1][5], work_orders[1][6] = assignable[0], 6.5
    first_preventive = next(w for w in work_orders if w[2] == "preventive")
    parts_used.append((first_preventive[0], 11, 2))
    first_corrective = next(w for w in work_orders if w[2] == "corrective")
    have = {(w, p) for w, p, _ in parts_used}
    for part_id in general_parts[:3]:                               # a corrective order with >= 3 lines
        if (first_corrective[0], part_id) not in have:
            parts_used.append((first_corrective[0], part_id, 2))
    con.executemany("INSERT INTO work_orders VALUES (?, ?, ?, ?, ?, ?, ?)", work_orders)
    con.executemany("INSERT INTO parts_used VALUES (?, ?, ?)", sorted(set(parts_used)))

    # ---- downtime events (independent of work orders; some machines have none)
    events = []
    event_id = 0
    for m in machines:
        machine_id = m[0]
        if machine_id in busy_machines:
            n = rng.randint(3, 5)
        else:
            n = rng.choices([0, 1, 2, 3], [0.35, 0.3, 0.2, 0.15])[0]
        for _ in range(n):
            event_id += 1
            start = _date(rng, dt.date(2024, 1, 1), dt.date(2025, 12, 20))
            cause = None if rng.random() < 0.2 else rng.choice(CAUSES)
            events.append([event_id, machine_id, start.isoformat(), round(rng.uniform(0.5, 30.0), 1), cause])
    events[0][4] = None
    con.executemany("INSERT INTO downtime_events VALUES (?, ?, ?, ?, ?)", events)
    con.commit()
    con.execute("VACUUM")
    con.close()
    assert empty_site == n_sites  # documented invariant: the last site has no machines


def dump(path: str | Path) -> str:
    """Logical contents as SQL text (file bytes can differ between SQLite versions)."""
    con = sqlite3.connect(path)
    text = "\n".join(con.iterdump())
    con.close()
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the synthetic maintenance database.")
    ap.add_argument("--check", action="store_true", help="regenerate and compare with the committed file")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out", type=Path, default=DB_PATH)
    args = ap.parse_args()
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            fresh = Path(tmp) / "fresh.db"
            build(fresh, args.seed)
            same = dump(fresh) == dump(args.out)
        print("contents match the committed database" if same else "MISMATCH with the committed database")
        return 0 if same else 1
    build(args.out, args.seed)
    con = sqlite3.connect(args.out)
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        print(f"{table:<16}{con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]:>5} rows")
    con.close()
    print(f"wrote {args.out} ({args.out.stat().st_size / 1024:.0f} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
