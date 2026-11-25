"""Run one .sql file against the lesson database and print the result.

    python labs/w2d1_sql_joins_grain/lab/run.py labs/w2d1_sql_joins_grain/lab/queries/q1_machines_per_site.sql
    python labs/w2d1_sql_joins_grain/lab/run.py <file.sql> --limit 10
    python labs/w2d1_sql_joins_grain/lab/run.py -c "SELECT COUNT(*) FROM work_orders"
"""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "data" / "maintenance.db"


def main() -> None:
    ap = argparse.ArgumentParser(description="Run a SQL file (or -c text) on maintenance.db")
    ap.add_argument("file", nargs="?", type=Path)
    ap.add_argument("-c", "--command", help="SQL text instead of a file")
    ap.add_argument("--limit", type=int, default=40, help="maximum rows to print")
    ap.add_argument("--db", type=Path, default=DB)
    args = ap.parse_args()
    sql = args.command or args.file.read_text()
    con = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    widths = [max(len(n), *(len(_fmt(r[i])) for r in rows[:args.limit])) if rows else len(n)
              for i, n in enumerate(names)]
    print("  ".join(n.ljust(w) for n, w in zip(names, widths)))
    print("  ".join("-" * w for w in widths))
    for r in rows[:args.limit]:
        print("  ".join(_fmt(v).ljust(w) for v, w in zip(r, widths)))
    print(f"({len(rows)} rows{', first ' + str(args.limit) + ' shown' if len(rows) > args.limit else ''})")


def _fmt(value) -> str:
    if value is None:
        return "NULL"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


if __name__ == "__main__":
    main()
