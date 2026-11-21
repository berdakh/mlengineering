-- Interview rep reference: longest run of consecutive login days per user.
-- logins(user_id, login_date) may contain several rows per user and day.
WITH days AS (
    SELECT DISTINCT user_id, login_date FROM logins
),
keyed AS (
    SELECT user_id, login_date,
           julianday(login_date) - ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY login_date) AS island
    FROM days
),
streaks AS (
    SELECT user_id, MIN(login_date) AS streak_start, COUNT(*) AS streak_days
    FROM keyed
    GROUP BY user_id, island
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY streak_days DESC, streak_start) AS rn
    FROM streaks
)
SELECT user_id, streak_start, streak_days
FROM ranked
WHERE rn = 1
ORDER BY user_id;
