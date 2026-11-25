-- grain: one row per technician who appears on no work order
SELECT tech_id, tech_name
FROM technicians
WHERE tech_id NOT IN (SELECT tech_id FROM work_orders);
