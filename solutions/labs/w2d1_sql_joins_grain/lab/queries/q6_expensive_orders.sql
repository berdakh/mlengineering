-- grain: one row per corrective work order whose parts cost is at least 1500
SELECT w.wo_id,
       COUNT(*)                        AS n_part_lines,
       SUM(pu.quantity * p.unit_cost)  AS parts_cost
FROM work_orders AS w
JOIN parts_used AS pu ON pu.wo_id = w.wo_id
JOIN parts AS p       ON p.part_id = pu.part_id
WHERE w.wo_type = 'corrective'                 -- row filter: before grouping
GROUP BY w.wo_id
HAVING SUM(pu.quantity * p.unit_cost)   >= 1500  -- group filter: after aggregation
ORDER BY parts_cost DESC, w.wo_id ASC;
