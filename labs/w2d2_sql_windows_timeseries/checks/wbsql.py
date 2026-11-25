"""Helpers shared by the w2d2 lab and challenge checks."""
from __future__ import annotations

import importlib.util
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

UNIT_DIR = Path(__file__).resolve().parents[1]
SHIPPED_DB = UNIT_DIR / "data" / "coldchain.db"
MIN_SQLITE = (3, 28, 0)          # window functions 3.25; RANGE with an offset and the WINDOW clause 3.28


def load_make_db():
    spec = importlib.util.spec_from_file_location("w2d2_make_db", UNIT_DIR / "data" / "make_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def connect_readonly(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def read_sql_file(path: Path) -> str:
    assert path.is_file(), f"missing file: {path.name} (expected at {path})"
    sql = path.read_text().strip()
    body = "\n".join(line for line in sql.splitlines() if not line.strip().startswith("--")).strip().rstrip(";")
    assert body, f"{path.name} contains no SQL statement yet"
    assert ";" not in body, f"{path.name} must contain exactly one statement (a WITH ... SELECT is one statement)"
    return sql.rstrip().rstrip(";")


def run_sql(con: sqlite3.Connection, sql: str) -> pd.DataFrame:
    try:
        cur = con.execute(sql)
    except sqlite3.Error as exc:                      # show the database error, not a traceback wall
        raise AssertionError(f"SQLite rejected the query: {exc}") from None
    columns = [c[0] for c in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=columns)


def assert_same_table(got: pd.DataFrame, expected_rows: list[dict], keys: list[str], what: str) -> None:
    """Order-insensitive comparison: same columns (any order), same rows, numeric tolerance 1e-6."""
    expected = pd.DataFrame(expected_rows)
    assert isinstance(got, pd.DataFrame), f"{what}: expected a table/DataFrame, got {type(got).__name__}"
    missing, extra = set(expected.columns) - set(got.columns), set(got.columns) - set(expected.columns)
    assert not missing and not extra, (
        f"{what}: column names differ from the specification. missing={sorted(missing)} unexpected={sorted(extra)}")
    assert not got.duplicated(subset=keys).any(), (
        f"{what}: the result has more than one row per {keys}; check the grain of your query")
    assert len(got) == len(expected), f"{what}: expected {len(expected)} rows (one per {keys}), got {len(got)}"
    got = got.sort_values(keys).reset_index(drop=True)
    expected = expected.sort_values(keys).reset_index(drop=True)
    for column in expected.columns:
        g, e = got[column], expected[column]
        g_null, e_null = g.isna().to_numpy(), e.isna().to_numpy()
        assert (g_null == e_null).all(), (
            f"{what}: column '{column}' has NULLs in different rows than expected "
            f"({int(g_null.sum())} NULLs, expected {int(e_null.sum())})")
        gv, ev = g[~g_null], e[~e_null]
        if pd.api.types.is_numeric_dtype(ev) or pd.api.types.is_bool_dtype(ev):
            try:
                close = np.isclose(gv.astype(float).to_numpy(), ev.astype(float).to_numpy(), rtol=0, atol=1e-6)
            except (TypeError, ValueError):
                raise AssertionError(f"{what}: column '{column}' should be numeric") from None
        else:
            close = gv.astype(str).to_numpy() == ev.astype(str).to_numpy()
        n_bad = int((~close).sum())
        assert n_bad == 0, f"{what}: column '{column}' differs from the expected values in {n_bad} of {len(ev)} rows"
