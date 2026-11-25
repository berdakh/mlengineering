-- grain: one row per work-order type
SELECT wo_type,
       COUNT(*)                                          AS n_orders,
       SUM(CASE WHEN closed_date IS NULL THEN 1 ELSE 0 END) AS n_open,
       COUNT(*) - COUNT(tech_id)                         AS n_unassigned,
       AVG(labor_hours)                                  AS avg_labor_hours  -- NULLs are skipped
FROM work_orders
GROUP BY wo_type;
