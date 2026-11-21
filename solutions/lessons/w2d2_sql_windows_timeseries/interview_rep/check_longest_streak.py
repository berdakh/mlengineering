"""Runs the interview-rep reference query on a hand-checkable table and asserts the answer."""
import sqlite3
from pathlib import Path

ROWS = [
    ("u1", "2026-01-01"), ("u1", "2026-01-02"), ("u1", "2026-01-02"), ("u1", "2026-01-03"),   # 3 days (one duplicate)
    ("u1", "2026-01-10"), ("u1", "2026-01-11"),
    ("u2", "2026-01-30"), ("u2", "2026-01-31"), ("u2", "2026-02-01"), ("u2", "2026-02-02"),   # 4 days across a month end
    ("u2", "2026-02-10"),
    ("u3", "2026-03-05"),                                                                       # single day
    ("u4", "2026-01-01"), ("u4", "2026-01-02"), ("u4", "2026-01-05"), ("u4", "2026-01-06"),   # two streaks of 2: earliest wins
]
con = sqlite3.connect(":memory:")
con.execute("CREATE TABLE logins (user_id TEXT, login_date TEXT)")
con.executemany("INSERT INTO logins VALUES (?, ?)", ROWS)
got = con.execute((Path(__file__).parent / "longest_streak.sql").read_text()).fetchall()
expected = [("u1", "2026-01-01", 3), ("u2", "2026-01-30", 4), ("u3", "2026-03-05", 1), ("u4", "2026-01-01", 2)]
assert got == expected, got
print("ok:", got)
