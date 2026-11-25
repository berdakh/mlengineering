-- grain: one row per machine (all machines)
-- key: machine_id
SELECT m.machine_id,
       COUNT(pu.part_id)              AS n_distinct_parts,
       COALESCE(SUM(pu.quantity), 0)  AS total_quantity
FROM machines AS m
LEFT JOIN work_orders AS w ON w.machine_id = m.machine_id
LEFT JOIN parts_used AS pu ON pu.wo_id = w.wo_id
GROUP BY m.machine_id;
