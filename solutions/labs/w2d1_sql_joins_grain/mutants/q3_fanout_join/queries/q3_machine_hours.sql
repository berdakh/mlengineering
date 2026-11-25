-- grain: one row per machine
SELECT m.machine_id,
       COUNT(DISTINCT w.wo_id)          AS n_work_orders,
       COALESCE(SUM(w.labor_hours), 0)  AS labor_hours,
       COALESCE(SUM(d.hours), 0)        AS downtime_hours
FROM machines AS m
LEFT JOIN work_orders AS w     ON w.machine_id = m.machine_id
LEFT JOIN downtime_events AS d ON d.machine_id = m.machine_id
GROUP BY m.machine_id;
