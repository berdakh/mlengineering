-- grain: one row per site
SELECT s.site_id,
       COUNT(w.wo_id) AS n_corrective_2025
FROM sites AS s
LEFT JOIN machines AS m    ON m.site_id = s.site_id
LEFT JOIN work_orders AS w ON w.machine_id = m.machine_id
WHERE w.wo_type = 'corrective'
  AND w.opened_date >= '2025-01-01' AND w.opened_date < '2026-01-01'
GROUP BY s.site_id;
