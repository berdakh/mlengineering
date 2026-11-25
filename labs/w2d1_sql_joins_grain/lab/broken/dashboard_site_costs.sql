-- Query behind the "Maintenance cost by site" dashboard tile. Finance says the labour
-- hours are far too high and that some work orders seem to be missing. Do not edit this
-- file: diagnose it, then write the corrected query in ../queries/q7_site_costs_fixed.sql
SELECT s.site_id,
       COUNT(w.wo_id)                  AS n_work_orders,
       SUM(w.labor_hours)              AS labor_hours,
       SUM(pu.quantity * p.unit_cost)  AS parts_cost
FROM sites AS s
JOIN machines AS m     ON m.site_id = s.site_id
JOIN work_orders AS w  ON w.machine_id = m.machine_id
JOIN parts_used AS pu  ON pu.wo_id = w.wo_id
JOIN parts AS p        ON p.part_id = pu.part_id
GROUP BY s.site_id;
