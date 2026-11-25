"""Optional extension: run your lab queries on DuckDB and compare with SQLite.

DuckDB is not a course dependency. Install it only if you want this comparison:
    python -m pip install duckdb
    python labs/w2d1_sql_joins_grain/example/run_on_duckdb.py [queries_dir]

Tables are copied from data/maintenance.db (SYNTHETIC) into an in-memory DuckDB database.
A query that SQLite accepts and DuckDB rejects is usually relying on SQLite's leniency
(for example a non-aggregated column that is not in GROUP BY).
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "data" / "maintenance.db"
TABLES = ("sites", "machines", "technicians", "work_orders", "parts", "parts_used", "downtime_events")


def strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines()).strip().rstrip(";")


def canonical(rows) -> list[tuple]:
    def norm(v):
        return None if v is None else (round(float(v), 4) if isinstance(v, (int, float)) else str(v))
    return sorted((tuple(norm(v) for v in r) for r in rows), key=repr)


def main() -> int:
    try:
        import duckdb
    except ImportError:
        print("duckdb is not installed; this extension is optional (python -m pip install duckdb)")
        return 0
    queries = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "lab" / "queries"
    lite = sqlite3.connect(DB)
    duck = duckdb.connect()
    for table in TABLES:
        frame = pd.read_sql_query(f"SELECT * FROM {table}", lite)  # noqa: F841 (used by DuckDB below)
        duck.execute(f"CREATE TABLE {table} AS SELECT * FROM frame")
    print(f"DuckDB {duckdb.__version__} vs SQLite {sqlite3.sqlite_version}")
    for path in sorted(queries.glob("*.sql")):
        sql = strip_comments(path.read_text())
        try:
            a = canonical(lite.execute(sql).fetchall())
            b = canonical(duck.execute(sql).fetchall())
            print(f"{'same     ' if a == b else 'DIFFERENT'} {path.name}")
        except Exception as exc:  # report and continue with the next query
            print(f"error     {path.name}: {str(exc).splitlines()[0][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
