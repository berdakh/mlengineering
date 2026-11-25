"""Reference for the w2d1 interview rep: executes the model answer and the common wrong answer
on a tiny in-memory database (SYNTHETIC) so the difference is visible.

    python solutions/labs/w2d1_sql_joins_grain/interview_rep/country_summary.py
"""
import sqlite3

SETUP = """
CREATE TABLE users (user_id INTEGER PRIMARY KEY, country TEXT);            -- country NULL = unknown
CREATE TABLE sessions (session_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, started_at TEXT NOT NULL);
CREATE TABLE purchases (purchase_id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, amount REAL NOT NULL);
INSERT INTO users VALUES (1,'KZ'),(2,'KZ'),(3,'DE'),(4,'DE'),(5,NULL),(6,'FR');
INSERT INTO sessions VALUES (1,1,'2026-01-01'),(2,1,'2026-01-02'),(3,1,'2026-01-03'),
                            (4,2,'2026-01-01'),(5,3,'2026-01-05'),(6,3,'2026-01-06'),(7,5,'2026-01-07');
INSERT INTO purchases VALUES (1,1,10.0),(2,1,30.0),(3,3,25.0),(4,5,40.0);
"""

MODEL = """
WITH s AS (SELECT user_id, COUNT(*) AS n_sessions FROM sessions GROUP BY user_id),
     p AS (SELECT user_id, SUM(amount) AS revenue FROM purchases GROUP BY user_id)
SELECT COALESCE(u.country, 'unknown')              AS country,
       COUNT(*)                                    AS n_users,
       COUNT(p.user_id)                            AS n_buyers,
       COALESCE(SUM(p.revenue), 0)                 AS revenue,
       1.0 * COALESCE(SUM(s.n_sessions), 0) / COUNT(*) AS sessions_per_user
FROM users AS u
LEFT JOIN s ON s.user_id = u.user_id
LEFT JOIN p ON p.user_id = u.user_id
GROUP BY COALESCE(u.country, 'unknown')
ORDER BY country;
"""

NAIVE = """
SELECT u.country,
       COUNT(DISTINCT u.user_id)                           AS n_users,
       COUNT(DISTINCT p.user_id)                           AS n_buyers,
       SUM(p.amount)                                       AS revenue,
       1.0 * COUNT(s.session_id) / COUNT(DISTINCT u.user_id) AS sessions_per_user
FROM users AS u
LEFT JOIN sessions AS s  ON s.user_id = u.user_id
LEFT JOIN purchases AS p ON p.user_id = u.user_id
GROUP BY u.country
ORDER BY u.country;
"""

con = sqlite3.connect(":memory:")
con.executescript(SETUP)
for title, sql in (("model answer", MODEL), ("common wrong answer (two children joined, then aggregated)", NAIVE)):
    cur = con.execute(sql)
    print(f"\n-- {title}\n   " + " | ".join(d[0] for d in cur.description))
    for row in cur:
        print("   " + " | ".join("NULL" if v is None else str(v) for v in row))
print("\ncheck: total revenue from purchases =", con.execute("SELECT SUM(amount) FROM purchases").fetchone()[0])
