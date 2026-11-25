-- Q2 (top-n per group with a window function). Reference.
-- grain: one row per (city, driver) for the top two drivers of each city
WITH counts AS (
    SELECT t.city_id, t.driver_id, COUNT(*) AS completed_trips
    FROM trips t
    WHERE t.status = 'completed'
      AND t.requested_at >= '2026-03-01' AND t.requested_at < '2026-04-01'
    GROUP BY t.city_id, t.driver_id
),
ranked AS (
    SELECT city_id, driver_id, completed_trips,
           ROW_NUMBER() OVER (PARTITION BY city_id ORDER BY completed_trips DESC, driver_id ASC) AS rnk
    FROM counts
)
SELECT c.name AS city, r.driver_id, r.completed_trips, r.rnk AS rank
FROM ranked r JOIN cities c ON c.city_id = r.city_id
WHERE r.rnk <= 2
ORDER BY city, rank;
