"""Convenience runner:  python lessons/w8d6_final_assessment/f2_sql/lab/explore.py q1.sql
                        python lessons/w8d6_final_assessment/f2_sql/lab/explore.py "SELECT * FROM complaints LIMIT 5"
"""
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parents[1] / "data" / "parcelo.db"

arg = sys.argv[1] if len(sys.argv) > 1 else "SELECT name, sql FROM sqlite_master WHERE type='table'"
sql = (HERE / arg).read_text() if arg.endswith(".sql") else arg
conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
cur = conn.execute(sql)
rows = cur.fetchall()
print(" | ".join(d[0] for d in cur.description))
for row in rows[:25]:
    print(" | ".join(str(v) for v in row))
print(f"({len(rows)} rows)")
