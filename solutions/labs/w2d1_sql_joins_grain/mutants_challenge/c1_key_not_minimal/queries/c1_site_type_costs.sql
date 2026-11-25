-- grain: one row per (site, work-order type) that has at least one work order
-- key: site_id, wo_type, n_orders
WITH wo_parts AS (
    SELECT pu.wo_id, SUM(pu.quantity * p.unit_cost) AS parts_cost
    FROM parts_used AS pu
    JOIN parts AS p ON p.part_id = pu.part_id
    GROUP BY pu.wo_id
)
SELECT m.site_id,
       w.wo_type,
       COUNT(*)                          AS n_orders,
       COALESCE(SUM(wp.parts_cost), 0.0) AS parts_cost
FROM work_orders AS w
JOIN machines AS m       ON m.machine_id = w.machine_id
LEFT JOIN wo_parts AS wp ON wp.wo_id = w.wo_id
GROUP BY m.site_id, w.wo_type;
