"""Fixtures for the w2d2 challenge checks. Grades <target>/features.sql."""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "checks"))
from tools.wbcheck import resolve_target  # noqa: E402

import wbsql  # noqa: E402

UNIT = "lessons/w2d2_sql_windows_timeseries"


@pytest.fixture(scope="session")
def feature_sql() -> str:
    target = resolve_target(UNIT, "challenge")
    assert sqlite3.sqlite_version_info >= wbsql.MIN_SQLITE, f"SQLite {sqlite3.sqlite_version} is too old for this unit"
    return wbsql.read_sql_file(target / "features.sql")


@pytest.fixture(scope="session")
def databases(tmp_path_factory) -> dict[str, Path]:
    work = tmp_path_factory.mktemp("w2d2c")
    reseeded = work / "reseeded.db"
    wbsql.load_make_db().build(reseeded, seed=77)
    scratch = work / "scratch.db"                   # writable copy for the perturbation tests
    shutil.copy(wbsql.SHIPPED_DB, scratch)
    return {"shipped": wbsql.SHIPPED_DB, "reseeded": reseeded, "scratch": scratch}
