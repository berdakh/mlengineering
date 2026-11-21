-- grain: one row per technician who appears on no work order
SELECT t.tech_id, t.tech_name
FROM technicians AS t
WHERE NOT EXISTS (SELECT 1 FROM work_orders AS w WHERE w.tech_id = t.tech_id);
