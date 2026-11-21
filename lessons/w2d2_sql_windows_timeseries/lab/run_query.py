"""Run one of your .sql files against the lesson database and print the result.

    python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q1                  # first 12 rows
    python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q5 --rows 40
    python lessons/w2d2_sql_windows_timeseries/lab/run_query.py q3 --where "device_id = 'D01'"
    python lessons/w2d2_sql_windows_timeseries/lab/run_query.py --sql "SELECT * FROM calibration"
    python lessons/w2d2_sql_windows_timeseries/lab/run_query.py ../challenge/features.sql

The database is opened read-only, so nothing you run here can damage it.
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "data" / "coldchain.db"


def find(name: str) -> Path:
    candidates = [Path(name), HERE / name, *sorted((HERE / "queries").glob(f"{name}*.sql"))]
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit(f"no query file matches '{name}' (looked in {HERE / 'queries'})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query", nargs="?", help="q1..q6, or a path to a .sql file")
    ap.add_argument("--sql", help="run this SQL text instead of a file")
    ap.add_argument("--rows", type=int, default=12, help="rows to print (default 12)")
    ap.add_argument("--where", help="filter applied to the RESULT of your query, e.g. \"device_id = 'D01'\"")
    ap.add_argument("--db", default=str(DB))
    args = ap.parse_args()
    if not (args.query or args.sql):
        ap.error("give a query name or --sql")
    sql = args.sql or find(args.query).read_text()
    sql = sql.strip().rstrip(";")
    if args.where:
        sql = f"SELECT * FROM (\n{sql}\n) WHERE {args.where}"
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        frame = pd.read_sql_query(sql, con)
    except Exception as exc:  # show the database message without a traceback
        raise SystemExit(f"query failed: {exc}")
    finally:
        con.close()
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(frame.head(args.rows).to_string(index=False))
    print(f"[{len(frame)} rows x {frame.shape[1]} columns; SQLite {sqlite3.sqlite_version}]")


if __name__ == "__main__":
    main()
