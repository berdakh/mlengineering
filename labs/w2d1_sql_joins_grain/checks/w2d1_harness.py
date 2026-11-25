"""Run a learner's .sql file against a database and compare result sets.

Comparison rules (behaviour, not implementation):
  * column NAMES must match the task (case-insensitive); column order is free
  * row order is ignored unless the task asks for an ordering
  * numbers are compared after rounding to 4 decimals; 3 and 3.0 are equal; NULL only equals NULL
"""
from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.wbcheck import resolve_target  # noqa: E402

UNIT = "labs/w2d1_sql_joins_grain"
DATA_DIR = ROOT / UNIT / "data"
COMMITTED_DB = DATA_DIR / "maintenance.db"
RESEED = 4242  # the second database: same schema and guarantees, different rows


def load_make_db():
    spec = importlib.util.spec_from_file_location("w2d1_make_db", DATA_DIR / "make_db.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines()).strip()


def read_query(path: Path) -> str:
    assert path.is_file(), f"missing query file: {path.name}"
    body = strip_comments(path.read_text()).rstrip(";").strip()
    assert body, f"{path.name} contains no SQL yet"
    first = body.split(None, 1)[0].upper()
    assert first in ("SELECT", "WITH"), f"{path.name} must be a single SELECT (CTEs allowed), found {first}"
    return body


def run_query(db: Path, path: Path) -> tuple[list[str], list[tuple]]:
    sql = read_query(path)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        cur = con.execute(sql)
        columns = [d[0].lower() for d in cur.description]
        rows = cur.fetchall()
    except sqlite3.Error as exc:  # surface the SQL error as a readable failure
        raise AssertionError(f"{path.name} failed to run: {exc}") from exc
    finally:
        con.close()
    return columns, rows


def _norm(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    return str(value)


def _sort_key(row: tuple):
    return tuple((v is None, "" if v is None else (v if isinstance(v, str) else ""),
                  0.0 if v is None or isinstance(v, str) else v) for v in row)


def normalise(columns: list[str], rows: list[tuple], expected_columns: list[str]) -> list[tuple]:
    assert len(set(columns)) == len(columns), f"duplicate column names in result: {columns}"
    assert sorted(columns) == sorted(expected_columns), (
        f"result columns {columns} do not match the required columns {expected_columns}")
    index = [columns.index(c) for c in expected_columns]
    return [tuple(_norm(row[i]) for i in index) for row in rows]


def assert_same_result(got: tuple[list[str], list[tuple]], expected_columns: list[str],
                       expected_rows: list[tuple], ordered: bool = False, label: str = "") -> None:
    got_rows = normalise(got[0], got[1], expected_columns)
    exp_rows = [tuple(_norm(v) for v in row) for row in expected_rows]
    if not ordered:
        got_rows, exp_rows = sorted(got_rows, key=_sort_key), sorted(exp_rows, key=_sort_key)
    if got_rows == exp_rows:
        return
    missing = [r for r in exp_rows if r not in got_rows][:3]
    extra = [r for r in got_rows if r not in exp_rows][:3]
    hint = ("row order differs from the requested ordering" if sorted(got_rows, key=_sort_key)
            == sorted(exp_rows, key=_sort_key) else
            f"expected {len(exp_rows)} rows, got {len(got_rows)}; "
            f"examples expected-but-absent {missing}; examples present-but-wrong {extra}")
    raise AssertionError(f"{label}: wrong result ({hint}). Columns: {expected_columns}")


def declared_header(path: Path, tag: str) -> str | None:
    """Value of a ``-- <tag>: ...`` comment line, or None."""
    for line in path.read_text().splitlines():
        m = re.match(rf"\s*--\s*{tag}\s*:\s*(.*)$", line, flags=re.I)
        if m:
            return m.group(1).strip()
    return None
