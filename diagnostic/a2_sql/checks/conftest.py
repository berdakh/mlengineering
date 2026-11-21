import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

TARGET = resolve_target("diagnostic/a2_sql")
DB = ROOT / "diagnostic" / "data" / "streambox.db"


def _connect():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)  # read-only: a query cannot damage the data


@pytest.fixture(scope="session")
def tables():
    """The three tables as DataFrames; expected answers are computed from these with pandas,
    independently of any SQL."""
    conn = _connect()
    out = {t: pd.read_sql(f"SELECT * FROM {t}", conn) for t in ("customers", "invoices", "tickets")}
    conn.close()
    return out


@pytest.fixture(scope="session")
def run_sql():
    def run(name: str):
        path = TARGET / name
        assert path.is_file(), f"missing {path}"
        conn = _connect()
        try:
            cur = conn.execute(path.read_text())
            rows = cur.fetchall()
            ncols = len(cur.description or [])
        finally:
            conn.close()
        return rows, ncols
    return run
