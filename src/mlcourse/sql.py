"""SQL in notebooks without any setup: SQLite is part of Python, so this works in Colab and locally.

    from mlcourse.sql import sql, tables, schema
    tables("shop")                      # which tables are in the shop database?
    schema("shop", "orders")            # columns and types of one table
    sql("SELECT * FROM orders LIMIT 5", "shop")   # a pandas DataFrame

Databases are small files in data/course/<name>.db, committed to the repository and rebuilt by
data/course/make_<name>.py. Queries run read-only, so an experiment can never damage the data.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from mlcourse.paths import repo_root


def db_path(name: str) -> Path:
    path = repo_root() / "data" / "course" / f"{name}.db"
    if not path.is_file():
        raise FileNotFoundError(f"no course database {name!r} (expected {path})")
    return path


def connect(name: str) -> sqlite3.Connection:
    """A read-only connection to a course database."""
    return sqlite3.connect(f"file:{db_path(name)}?mode=ro", uri=True)


def sql(query: str, db: str = "shop"):
    """Run a query and return the result as a pandas DataFrame."""
    import pandas as pd

    with connect(db) as con:
        return pd.read_sql_query(query, con)


def tables(db: str = "shop") -> list[str]:
    q = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    with connect(db) as con:
        return [r[0] for r in con.execute(q)]


def schema(db: str, table: str):
    import pandas as pd

    with connect(db) as con:
        rows = con.execute(f"PRAGMA table_info({table})").fetchall()
    return pd.DataFrame(rows, columns=["cid", "column", "type", "notnull", "default", "pk"])[["column", "type", "pk"]]
