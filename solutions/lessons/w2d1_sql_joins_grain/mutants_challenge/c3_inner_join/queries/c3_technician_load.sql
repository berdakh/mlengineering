-- grain: one row per technician
-- key: tech_id
SELECT t.tech_id,
       COUNT(w.wo_id)               AS n_orders,
       SUM(w.labor_hours)           AS labor_hours,
       COUNT(DISTINCT w.machine_id) AS n_machines
FROM technicians AS t
JOIN work_orders AS w ON w.tech_id = t.tech_id
GROUP BY t.tech_id;
