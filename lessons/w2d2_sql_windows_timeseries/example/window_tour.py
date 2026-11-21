"""Worked example for w2d2: five window-function patterns, each checked against pandas.

A hand-written log of 14 scan events from two packaging lines (SYNTHETIC, typed by hand so
that every row can be followed by eye). Run from anywhere:

    python lessons/w2d2_sql_windows_timeseries/example/window_tour.py
"""
from __future__ import annotations

import sqlite3

import pandas as pd

ROWS = [
    # event_id, line, ts,                 operator, units
    (1,  "A", "2026-05-04 08:00:00", "ines",  40),
    (2,  "A", "2026-05-04 08:10:00", "ines",  55),
    (3,  "A", "2026-05-04 08:10:00", "omar",  55),   # same second as event 2: a tie in time AND in units
    (4,  "A", "2026-05-04 08:25:00", "omar",  30),
    (5,  "A", "2026-05-04 09:40:00", "ines",  70),   # 75 min after event 4: a new session
    (6,  "A", "2026-05-04 09:55:00", "ines",  20),
    (7,  "B", "2026-05-04 08:05:00", "li",    10),
    (8,  "B", "2026-05-04 08:20:00", "li",    90),
    (9,  "B", "2026-05-04 08:20:00", "li",    90),   # exact re-send of event 8 (duplicate)
    (10, "B", "2026-05-04 08:45:00", "sam",   60),
    (11, "B", "2026-05-04 10:30:00", "sam",   15),   # 105 min gap
    (12, "B", "2026-05-04 10:40:00", "li",    35),
    (13, "B", "2026-05-04 11:30:00", "li",    80),   # 50 min gap
    (14, "B", "2026-05-04 11:35:00", "sam",   25),
]
COLUMNS = ["event_id", "line", "ts", "operator", "units"]


def show(title: str, frame: pd.DataFrame) -> None:
    print(f"\n--- {title} ---")
    print(frame.to_string(index=False))


def same(a: pd.DataFrame, b: pd.DataFrame, keys: list[str]) -> None:
    a = a.sort_values(keys).reset_index(drop=True)
    b = b.sort_values(keys).reset_index(drop=True)[a.columns]
    pd.testing.assert_frame_equal(a, b, check_dtype=False)


def main() -> None:
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE scans (event_id INTEGER PRIMARY KEY, line TEXT, ts TEXT, operator TEXT, units INTEGER)")
    con.executemany("INSERT INTO scans VALUES (?, ?, ?, ?, ?)", ROWS)
    df = pd.DataFrame(ROWS, columns=COLUMNS)
    df["t"] = pd.to_datetime(df["ts"])
    q = lambda sql: pd.read_sql_query(sql, con)  # noqa: E731
    print(f"SQLite {sqlite3.sqlite_version}, pandas {pd.__version__}")

    # 1. Three ranking functions on the same ordering. They differ only on ties.
    ranks = q("""
        SELECT event_id, line, units,
               ROW_NUMBER() OVER w AS row_number,
               RANK()       OVER w AS rank,
               DENSE_RANK() OVER w AS dense_rank
        FROM scans
        WHERE line = 'A'
        WINDOW w AS (PARTITION BY line ORDER BY units DESC)
        ORDER BY units DESC, event_id
    """)
    show("1. ranking functions on line A, ORDER BY units DESC", ranks)
    a = df[df.line == "A"]
    pd_ranks = a.assign(rank=a.units.rank(method="min", ascending=False).astype(int),
                        dense_rank=a.units.rank(method="dense", ascending=False).astype(int))
    same(ranks[["event_id", "rank", "dense_rank"]], pd_ranks[["event_id", "rank", "dense_rank"]], ["event_id"])

    # 2. Top-1 per group. A window result cannot be used in WHERE of the same SELECT
    #    (WHERE runs before windows), so it is computed in a CTE and filtered outside.
    top_ties = q("""
        WITH r AS (SELECT *, RANK() OVER (PARTITION BY line ORDER BY units DESC) AS rk FROM scans)
        SELECT line, event_id, units FROM r WHERE rk = 1 ORDER BY line, event_id
    """)
    show("2a. 'largest scan per line' with RANK: ties give several rows per line", top_ties)
    top_one = q("""
        WITH r AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY line ORDER BY units DESC, event_id) AS rn FROM scans)
        SELECT line, event_id, units FROM r WHERE rn = 1 ORDER BY line
    """)
    show("2b. ROW_NUMBER with a tie-breaker: exactly one row per line", top_one)
    pd_top = df.sort_values(["units", "event_id"], ascending=[False, True]).groupby("line").head(1)
    same(top_one, pd_top[["line", "event_id", "units"]], ["line"])

    # 3. Running total. The default frame is RANGE ... CURRENT ROW, and under RANGE the
    #    current row includes its peers (rows with an equal ORDER BY value).
    running = q("""
        SELECT event_id, ts, units,
               SUM(units) OVER (PARTITION BY line ORDER BY ts)                              AS default_frame,
               SUM(units) OVER (PARTITION BY line ORDER BY ts, event_id
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)           AS rows_frame
        FROM scans WHERE line = 'A' ORDER BY ts, event_id
    """)
    show("3. running total on line A: default frame versus explicit ROWS", running)
    pd_running = a.sort_values(["ts", "event_id"]).assign(rows_frame=lambda d: d.units.cumsum())
    same(running[["event_id", "rows_frame"]], pd_running[["event_id", "rows_frame"]], ["event_id"])

    # 4. De-duplicate, then sessionise: a new session starts after a gap of more than 30 minutes.
    sessions = q("""
        WITH dedup AS (
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY line, ts, operator, units ORDER BY event_id DESC) AS rn
                FROM scans)
            WHERE rn = 1
        ),
        gaps AS (
            SELECT *, (strftime('%s', ts) - strftime('%s', LAG(ts) OVER (PARTITION BY line ORDER BY ts, event_id))) / 60.0
                          AS gap_min
            FROM dedup
        ),
        numbered AS (
            SELECT *, SUM(CASE WHEN gap_min IS NULL OR gap_min > 30 THEN 1 ELSE 0 END)
                          OVER (PARTITION BY line ORDER BY ts, event_id
                                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_no
            FROM gaps
        )
        SELECT line, session_no, MIN(ts) AS start_ts, MAX(ts) AS end_ts, COUNT(*) AS n_scans, SUM(units) AS units
        FROM numbered
        GROUP BY line, session_no
        ORDER BY line, session_no
    """)
    show("4. de-duplicated, sessionised by a 30-minute gap", sessions)
    d = (df.sort_values("event_id", ascending=False).drop_duplicates(["line", "ts", "operator", "units"])
           .sort_values(["line", "t", "event_id"]))
    gap = d.groupby("line")["t"].diff()
    d["session_no"] = (gap.isna() | (gap > pd.Timedelta(minutes=30))).astype(int).groupby(d["line"]).cumsum()
    pd_sessions = (d.groupby(["line", "session_no"])
                    .agg(start_ts=("ts", "min"), end_ts=("ts", "max"), n_scans=("ts", "size"), units=("units", "sum"))
                    .reset_index())
    same(sessions, pd_sessions, ["line", "session_no"])

    # 5. Change since the previous scan by the same operator on the same line (LAG).
    lagged = q("""
        SELECT event_id, line, operator, units,
               units - LAG(units) OVER (PARTITION BY line, operator ORDER BY ts, event_id) AS change
        FROM scans WHERE line = 'A' ORDER BY operator, ts, event_id
    """)
    show("5. LAG within (line, operator) on line A", lagged)
    pd_lag = a.sort_values(["ts", "event_id"]).assign(change=lambda x: x.groupby(["line", "operator"]).units.diff())
    same(lagged[["event_id", "change"]], pd_lag[["event_id", "change"]], ["event_id"])

    print("\nAll five SQL results equal their pandas equivalents.")


if __name__ == "__main__":
    main()
