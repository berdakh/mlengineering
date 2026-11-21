-- grain: one row per part that was never used on a corrective work order
-- key: part_id
SELECT p.part_id, p.part_name
FROM parts AS p
WHERE NOT EXISTS (
    SELECT 1
    FROM parts_used AS pu
    JOIN work_orders AS w ON w.wo_id = pu.wo_id
    WHERE pu.part_id = p.part_id
      AND w.wo_type = 'corrective'
);
