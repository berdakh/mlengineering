"""Fixtures for the w2d2 lab checks. Grades <target>/queries/*.sql and <target>/pandas_equiv.py."""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from tools.wbcheck import resolve_target  # noqa: E402

import wbsql  # noqa: E402

UNIT = "labs/w2d2_sql_windows_timeseries"


@pytest.fixture(scope="session")
def target() -> Path:
    path = resolve_target(UNIT, "lab")
    assert path.is_dir(), f"target directory not found: {path}"
    return path


@pytest.fixture(scope="session", autouse=True)
def sqlite_is_recent_enough():
    version = sqlite3.sqlite_version_info
    assert version >= wbsql.MIN_SQLITE, (
        f"this lab needs SQLite >= {'.'.join(map(str, wbsql.MIN_SQLITE))}; your Python is linked against "
        f"{sqlite3.sqlite_version}. Use a newer Python build (see handbook H2.1).")


@pytest.fixture(scope="session")
def databases(tmp_path_factory) -> dict[str, Path]:
    """The committed database and a second one from another seed (SYNTHETIC, same schema)."""
    reseeded = tmp_path_factory.mktemp("w2d2") / "reseeded.db"
    wbsql.load_make_db().build(reseeded, seed=77)
    return {"shipped": wbsql.SHIPPED_DB, "reseeded": reseeded}


@pytest.fixture(params=["shipped", "reseeded"])
def con(request, databases):
    connection = wbsql.connect_readonly(databases[request.param])
    yield connection
    connection.close()


@pytest.fixture(scope="session")
def pandas_module(target):
    path = target / "pandas_equiv.py"
    assert path.is_file(), f"missing file: {path}"
    spec = importlib.util.spec_from_file_location("learner_pandas_equiv", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def frames(con):
    return {
        "readings": pd.read_sql_query("SELECT * FROM readings_dedup", con),
        "calibration": pd.read_sql_query("SELECT * FROM calibration", con),
    }
