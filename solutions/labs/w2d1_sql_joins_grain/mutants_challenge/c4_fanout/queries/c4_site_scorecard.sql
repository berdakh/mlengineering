-- grain: one row per site (all sites)
-- key: site_id
SELECT s.site_id,
       COUNT(DISTINCT m.machine_id)                    AS n_machines,
       COALESCE(SUM(d.hours), 0.0)                     AS downtime_hours,
       COALESCE(SUM(w.labor_hours), 0.0)               AS labor_hours,
       COALESCE(SUM(pu.quantity * p.unit_cost), 0.0)   AS parts_cost
FROM sites AS s
LEFT JOIN machines AS m        ON m.site_id = s.site_id
LEFT JOIN downtime_events AS d ON d.machine_id = m.machine_id
LEFT JOIN work_orders AS w     ON w.machine_id = m.machine_id
LEFT JOIN parts_used AS pu     ON pu.wo_id = w.wo_id
LEFT JOIN parts AS p           ON p.part_id = pu.part_id
GROUP BY s.site_id;
