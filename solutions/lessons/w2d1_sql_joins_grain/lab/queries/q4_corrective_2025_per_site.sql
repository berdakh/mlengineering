-- grain: one row per site (all sites)
-- The conditions on work_orders live in the ON clause: in WHERE they would discard the
-- NULL-extended rows and silently remove sites with no matching order.
SELECT s.site_id,
       COUNT(w.wo_id) AS n_corrective_2025
FROM sites AS s
LEFT JOIN machines AS m ON m.site_id = s.site_id
LEFT JOIN work_orders AS w
       ON w.machine_id = m.machine_id
      AND w.wo_type = 'corrective'
      AND w.opened_date >= '2025-01-01'
      AND w.opened_date <  '2026-01-01'
GROUP BY s.site_id;
