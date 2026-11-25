"""Fixtures for the w8d4 lab checks.

Python problems are imported from <target>/python/; SQL problems are read from <target>/sql/ and run on
the shipped SYNTHETIC database, on a database regenerated with a different seed, and on tiny hand-built
databases that contain the traps. Expected SQL results come from an independent pandas oracle.
"""
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
sys.path.insert(0, str(HERE))

from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "lessons/w8d4_coding_interviews"
DB = UNIT_DIR / "data" / "rides.db"


@pytest.fixture(scope="session")
def target() -> Path:
    return resolve_target(UNIT, "lab")


def load(target: Path, name: str):
    path = target / "python" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"w8d4_{name}_under_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def reseeded_db(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("db") / "rides_seed7.db"
    subprocess.run([sys.executable, str(UNIT_DIR / "data" / "make_db.py"), "--seed", "7", "--out", str(out)],
                   check=True, capture_output=True)
    return out


def run_sql(target: Path, query: str, db: Path) -> list[tuple]:
    sql = (target / "sql" / f"{query}.sql").read_text()
    con = sqlite3.connect(db)
    try:
        return [tuple(r) for r in con.execute(sql).fetchall()]
    finally:
        con.close()


SCHEMA = (UNIT_DIR / "data" / "make_db.py").read_text().split('SCHEMA = """', 1)[1].split('"""', 1)[0]


def tiny_db(tmp_path: Path, cities, drivers, trips, payments=()) -> Path:
    """A hand-built database with the course schema (riders are filled in automatically)."""
    path = tmp_path / "tiny.db"
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO cities VALUES (?, ?)", cities)
    con.executemany("INSERT INTO drivers VALUES (?, ?, ?)", drivers)
    con.executemany("INSERT INTO riders VALUES (?, ?)", [(1, "2025-01-01")])
    con.executemany("INSERT INTO trips VALUES (?, ?, 1, ?, ?, ?, ?)", trips)
    con.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?)", payments)
    con.commit()
    con.close()
    return path
