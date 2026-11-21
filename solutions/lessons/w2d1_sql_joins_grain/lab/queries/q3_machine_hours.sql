-- grain: one row per machine (all machines)
-- Both children are aggregated to the machine grain BEFORE joining, so neither multiplies the other.
WITH wo AS (
    SELECT machine_id, COUNT(*) AS n_work_orders, SUM(labor_hours) AS labor_hours
    FROM work_orders
    GROUP BY machine_id
),
dt AS (
    SELECT machine_id, SUM(hours) AS downtime_hours
    FROM downtime_events
    GROUP BY machine_id
)
SELECT m.machine_id,
       COALESCE(wo.n_work_orders, 0)   AS n_work_orders,
       COALESCE(wo.labor_hours, 0.0)   AS labor_hours,
       COALESCE(dt.downtime_hours, 0.0) AS downtime_hours
FROM machines AS m
LEFT JOIN wo ON wo.machine_id = m.machine_id
LEFT JOIN dt ON dt.machine_id = m.machine_id;
