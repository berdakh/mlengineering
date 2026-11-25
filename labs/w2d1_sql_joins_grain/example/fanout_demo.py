"""Worked example for w2d1: grain, fan-out and NULL semantics on a tiny in-memory database.

SYNTHETIC toy data in a familiar shape: EEG recordings, their channels, and annotated events.
Every statement the lesson makes about SQL behaviour is executed here, so you can check it
against your own SQLite build.

    python labs/w2d1_sql_joins_grain/example/fanout_demo.py
"""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE recordings (            -- grain: one row per recording
    recording_id INTEGER PRIMARY KEY,
    subject_id   TEXT NOT NULL,
    duration_s   REAL NOT NULL
);
CREATE TABLE channels (              -- grain: one row per (recording, channel)
    recording_id INTEGER NOT NULL REFERENCES recordings(recording_id),
    channel      TEXT NOT NULL,
    is_bad       INTEGER,            -- NULL = not yet reviewed
    PRIMARY KEY (recording_id, channel)
);
CREATE TABLE annotations (           -- grain: one row per annotated event
    annotation_id INTEGER PRIMARY KEY,
    recording_id  INTEGER NOT NULL REFERENCES recordings(recording_id),
    kind          TEXT NOT NULL,
    duration_s    REAL NOT NULL
);
INSERT INTO recordings VALUES (1, 'S01', 600), (2, 'S01', 300), (3, 'S02', 900), (4, 'S03', 450);
INSERT INTO channels VALUES
    (1, 'C3', 0), (1, 'C4', 0), (1, 'Cz', 1),
    (2, 'C3', 0), (2, 'C4', NULL),
    (3, 'C3', 0), (3, 'C4', 0), (3, 'Cz', 0), (3, 'Pz', NULL);
INSERT INTO annotations VALUES
    (1, 1, 'seizure', 40), (2, 1, 'artifact', 5),
    (3, 3, 'seizure', 65), (4, 3, 'seizure', 30), (5, 3, 'artifact', 10);
"""


def show(con: sqlite3.Connection, title: str, sql: str) -> None:
    cur = con.execute(sql)
    names = [d[0] for d in cur.description]
    rows = cur.fetchall()
    print(f"\n-- {title}")
    print("   " + " | ".join(names))
    for row in rows:
        print("   " + " | ".join("NULL" if v is None else str(v) for v in row))
    if not rows:
        print("   (no rows)")


def main() -> None:
    con = sqlite3.connect(":memory:")
    con.executescript(SCHEMA)
    print(f"SQLite {sqlite3.sqlite_version}")

    print("\n=== 1. Fan-out: the same question at three join shapes ===")
    show(con, "truth, from the table whose grain matches the measure",
         "SELECT SUM(duration_s) AS total_recorded_s FROM recordings")
    show(con, "WRONG: duration summed after joining channels (one row per channel)",
         """SELECT SUM(r.duration_s) AS total_recorded_s, COUNT(*) AS rows_summed
            FROM recordings r JOIN channels c ON c.recording_id = r.recording_id""")
    show(con, "WRONG: two one-to-many children joined to the same parent",
         """SELECT r.recording_id,
                   COUNT(*)            AS intermediate_rows,
                   COUNT(c.channel)    AS n_channels_reported,
                   SUM(a.duration_s)   AS event_s_reported
            FROM recordings r
            LEFT JOIN channels c    ON c.recording_id = r.recording_id
            LEFT JOIN annotations a ON a.recording_id = r.recording_id
            GROUP BY r.recording_id""")
    show(con, "RIGHT: each child aggregated to the parent grain, then joined",
         """WITH ch AS (SELECT recording_id, COUNT(*) AS n_channels FROM channels GROUP BY recording_id),
                 an AS (SELECT recording_id, SUM(duration_s) AS event_s FROM annotations GROUP BY recording_id)
            SELECT r.recording_id,
                   COALESCE(ch.n_channels, 0) AS n_channels,
                   COALESCE(an.event_s, 0)    AS event_s
            FROM recordings r
            LEFT JOIN ch ON ch.recording_id = r.recording_id
            LEFT JOIN an ON an.recording_id = r.recording_id""")

    print("\n=== 2. Row counts along a join chain (the cheapest diagnostic) ===")
    show(con, "how many rows after each step?",
         """SELECT (SELECT COUNT(*) FROM recordings) AS recordings,
                   (SELECT COUNT(*) FROM recordings r JOIN channels c USING (recording_id)) AS after_inner_channels,
                   (SELECT COUNT(*) FROM recordings r LEFT JOIN channels c USING (recording_id)) AS after_left_channels,
                   (SELECT COUNT(*) FROM recordings r LEFT JOIN channels c USING (recording_id)
                                                      LEFT JOIN annotations a USING (recording_id)) AS after_both""")

    print("\n=== 3. LEFT JOIN: a filter in WHERE versus in ON ===")
    show(con, "seizure count per recording, filter in ON (keeps recordings with none)",
         """SELECT r.recording_id, COUNT(a.annotation_id) AS n_seizures
            FROM recordings r
            LEFT JOIN annotations a ON a.recording_id = r.recording_id AND a.kind = 'seizure'
            GROUP BY r.recording_id""")
    show(con, "same filter in WHERE (recordings without seizures disappear)",
         """SELECT r.recording_id, COUNT(a.annotation_id) AS n_seizures
            FROM recordings r
            LEFT JOIN annotations a ON a.recording_id = r.recording_id
            WHERE a.kind = 'seizure'
            GROUP BY r.recording_id""")

    print("\n=== 4. NULL: three-valued logic ===")
    show(con, "comparisons with NULL are NULL (unknown), not false",
         """SELECT NULL = NULL AS null_eq_null, NULL <> 1 AS null_ne_1, NULL IS NULL AS null_is_null,
                   (NULL AND 0) AS null_and_false, (NULL OR 1) AS null_or_true,
                   (NULL AND 1) AS null_and_true, NOT NULL AS not_null""")
    show(con, "aggregates: COUNT(*) counts rows, COUNT(col)/SUM/AVG skip NULL",
         """SELECT COUNT(*) AS n_rows, COUNT(is_bad) AS n_reviewed, SUM(is_bad) AS n_bad,
                   AVG(is_bad) AS bad_rate_of_reviewed,
                   1.0 * SUM(is_bad) / COUNT(*) AS bad_rate_of_all
            FROM channels""")
    show(con, "over zero rows: COUNT is 0, SUM and AVG are NULL",
         "SELECT COUNT(*) AS n, SUM(duration_s) AS total, AVG(duration_s) AS mean FROM annotations WHERE kind = 'spike'")
    show(con, "WHERE keeps only TRUE: 'is_bad <> 1' silently drops unreviewed channels",
         """SELECT (SELECT COUNT(*) FROM channels WHERE is_bad = 1)  AS bad,
                   (SELECT COUNT(*) FROM channels WHERE is_bad <> 1) AS not_bad,
                   (SELECT COUNT(*) FROM channels)                   AS total""")

    print("\n=== 5. Anti-join: NOT IN versus NOT EXISTS when the list contains NULL ===")
    con.execute("CREATE TABLE reviewed (recording_id INTEGER)")   # nullable on purpose
    con.execute("INSERT INTO reviewed VALUES (1), (3), (NULL)")
    show(con, "NOT IN with a NULL in the list returns nothing",
         "SELECT recording_id FROM recordings WHERE recording_id NOT IN (SELECT recording_id FROM reviewed)")
    show(con, "NOT EXISTS answers the intended question",
         """SELECT r.recording_id FROM recordings r
            WHERE NOT EXISTS (SELECT 1 FROM reviewed v WHERE v.recording_id = r.recording_id)""")
    show(con, "LEFT JOIN ... IS NULL is an equivalent anti-join",
         """SELECT r.recording_id FROM recordings r
            LEFT JOIN reviewed v ON v.recording_id = r.recording_id
            WHERE v.recording_id IS NULL""")

    print("\n=== 6. Join types as row-set operations ===")
    show(con, "FULL OUTER JOIN keeps unmatched rows from both sides",
         """SELECT r.recording_id AS rec, v.recording_id AS reviewed_id
            FROM recordings r FULL OUTER JOIN reviewed v ON v.recording_id = r.recording_id
            ORDER BY rec IS NULL, rec""")
    show(con, "CROSS JOIN: every pairing (rows = 4 recordings x 2 kinds)",
         """SELECT COUNT(*) AS n_rows
            FROM recordings CROSS JOIN (SELECT DISTINCT kind FROM annotations)""")

    print("\n=== 7. GROUP BY: SQLite accepts a non-grouped, non-aggregated column ===")
    show(con, "subject_id grouped, recording_id is an ARBITRARY row's value (most engines reject this)",
         "SELECT subject_id, recording_id, SUM(duration_s) AS total_s FROM recordings GROUP BY subject_id")


if __name__ == "__main__":
    main()
