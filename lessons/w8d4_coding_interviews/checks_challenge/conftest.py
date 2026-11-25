"""Fixtures for the w8d4 challenge (45-minute mock): C1 in <target>/python, C2 in <target>/sql."""
from __future__ import annotations

import importlib.util
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
UNIT_DIR = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w8d4_coding_interviews"
DB = UNIT_DIR / "data" / "rides.db"
SCHEMA = (UNIT_DIR / "data" / "make_db.py").read_text().split('SCHEMA = """', 1)[1].split('"""', 1)[0]


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "challenge")


@pytest.fixture(scope="session")
def c1(target):
    path = target / "python" / "c1_longest_stable_run.py"
    spec = importlib.util.spec_from_file_location("w8d4_c1_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.longest_stable_run


@pytest.fixture(scope="session")
def reseeded_db(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("db") / "rides_seed7.db"
    subprocess.run([sys.executable, str(UNIT_DIR / "data" / "make_db.py"), "--seed", "7", "--out", str(out)],
                   check=True, capture_output=True)
    return out


def run_c2(target: Path, db: Path) -> list[tuple]:
    sql = (target / "sql" / "c2_driver_cohorts.sql").read_text()
    con = sqlite3.connect(db)
    try:
        return [(r[0], int(r[1]), int(r[2]), round(float(r[3]), 3)) for r in con.execute(sql).fetchall()]
    finally:
        con.close()


def tiny_db(tmp_path: Path, drivers, trips) -> Path:
    path = tmp_path / "tiny.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO cities VALUES (?, ?)", [(1, "North"), (2, "South")])
    con.executemany("INSERT INTO drivers VALUES (?, ?, ?)", drivers)
    con.executemany("INSERT INTO riders VALUES (?, ?)", [(1, "2025-01-01")])
    con.executemany("INSERT INTO trips VALUES (?, ?, 1, ?, ?, ?, ?)", trips)
    con.commit()
    con.close()
    return path
