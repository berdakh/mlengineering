-- grain: one row per site
SELECT s.site_id,
       s.site_name,
       COUNT(*)                                                     AS n_machines,
       SUM(CASE WHEN m.decommissioned_date IS NULL THEN 1 ELSE 0 END) AS n_active
FROM sites AS s
LEFT JOIN machines AS m ON m.site_id = s.site_id
GROUP BY s.site_id, s.site_name;
