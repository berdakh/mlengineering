-- C2 (mock, cohorts with a relative time window). Reference.
-- grain: one row per city that has at least one driver in the March 2026 cohort
WITH completed AS (
    SELECT driver_id, city_id, requested_at FROM trips WHERE status = 'completed'
),
first_trip AS (
    SELECT driver_id, MIN(requested_at) AS first_at FROM completed GROUP BY driver_id
),
cohort AS (
    SELECT f.driver_id, f.first_at, d.city_id
    FROM first_trip f JOIN drivers d ON d.driver_id = f.driver_id
    WHERE f.first_at >= '2026-03-01' AND f.first_at < '2026-04-01'
),
early AS (                                  -- completed trips in the 30 days starting at the first trip
    SELECT c.driver_id, COUNT(t.driver_id) AS n
    FROM cohort c
    LEFT JOIN completed t
      ON t.driver_id = c.driver_id
     AND t.requested_at >= c.first_at
     AND t.requested_at < '2026-04-01'
    GROUP BY c.driver_id
)
SELECT ci.name AS city,
       COUNT(*) AS cohort_size,
       SUM(CASE WHEN e.n >= 25 THEN 1 ELSE 0 END) AS active_drivers,
       ROUND(1.0 * SUM(CASE WHEN e.n >= 25 THEN 1 ELSE 0 END) / COUNT(*), 3) AS active_share
FROM cohort c
JOIN early e   ON e.driver_id = c.driver_id
JOIN cities ci ON ci.city_id = c.city_id
GROUP BY ci.city_id, ci.name
ORDER BY city;
