-- Q3 (gaps and islands). Reference.
-- grain: one row per driver with at least one completed trip
WITH days AS (                              -- one row per (driver, day): several trips a day count once
    SELECT DISTINCT driver_id, DATE(requested_at) AS day
    FROM trips
    WHERE status = 'completed'
),
islands AS (                                -- consecutive days share day - row_number
    SELECT driver_id, day,
           JULIANDAY(day) - ROW_NUMBER() OVER (PARTITION BY driver_id ORDER BY day) AS grp
    FROM days
),
streaks AS (
    SELECT driver_id, MIN(day) AS streak_start, COUNT(*) AS streak_length
    FROM islands
    GROUP BY driver_id, grp
),
best AS (
    SELECT driver_id, streak_start, streak_length,
           ROW_NUMBER() OVER (PARTITION BY driver_id ORDER BY streak_length DESC, streak_start DESC) AS r
    FROM streaks
)
SELECT driver_id, streak_start, streak_length
FROM best
WHERE r = 1
ORDER BY driver_id;
