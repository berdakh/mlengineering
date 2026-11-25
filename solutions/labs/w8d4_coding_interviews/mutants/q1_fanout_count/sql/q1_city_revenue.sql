-- Q1 (grain, joins, fan-out). Reference.
-- grain: one row per city (all cities, including those with no trips)
WITH march_completed AS (
    SELECT trip_id, city_id
    FROM trips
    WHERE status = 'completed'
      AND requested_at >= '2026-03-01' AND requested_at < '2026-04-01'
),
paid AS (                                   -- every attempt joined: fans out
    SELECT trip_id, CASE WHEN status = 'succeeded' THEN amount_cents END AS paid_cents
    FROM payments
)
SELECT c.name                                         AS city,
       COUNT(m.trip_id)                               AS completed_trips,
       COUNT(p.trip_id)                               AS paid_trips,
       ROUND(COALESCE(SUM(p.paid_cents), 0) / 100.0, 2) AS revenue
FROM cities c
LEFT JOIN march_completed m ON m.city_id = c.city_id
LEFT JOIN paid p            ON p.trip_id = m.trip_id
GROUP BY c.city_id, c.name
ORDER BY city;
