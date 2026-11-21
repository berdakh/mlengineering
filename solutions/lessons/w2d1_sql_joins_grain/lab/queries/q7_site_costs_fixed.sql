-- grain: one row per site (all sites)
-- Parts are first collapsed to one row per work order, so joining them cannot repeat labor_hours;
-- LEFT JOINs keep work orders without parts and sites without work orders.
WITH wo_parts AS (
    SELECT pu.wo_id, SUM(pu.quantity * p.unit_cost) AS parts_cost
    FROM parts_used AS pu
    JOIN parts AS p ON p.part_id = pu.part_id
    GROUP BY pu.wo_id
)
SELECT s.site_id,
       COUNT(w.wo_id)                       AS n_work_orders,
       COALESCE(SUM(w.labor_hours), 0.0)    AS labor_hours,
       COALESCE(SUM(wp.parts_cost), 0.0)    AS parts_cost
FROM sites AS s
LEFT JOIN machines AS m    ON m.site_id = s.site_id
LEFT JOIN work_orders AS w ON w.machine_id = m.machine_id
LEFT JOIN wo_parts AS wp   ON wp.wo_id = w.wo_id
GROUP BY s.site_id;
