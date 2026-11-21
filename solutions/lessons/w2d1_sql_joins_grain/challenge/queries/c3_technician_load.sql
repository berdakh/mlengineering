-- grain: one row per technician (all technicians, including never-assigned ones)
-- key: tech_id
SELECT t.tech_id,
       COUNT(w.wo_id)                    AS n_orders,
       COALESCE(SUM(w.labor_hours), 0.0) AS labor_hours,
       COUNT(DISTINCT w.machine_id)      AS n_machines
FROM technicians AS t
LEFT JOIN work_orders AS w ON w.tech_id = t.tech_id
GROUP BY t.tech_id;
