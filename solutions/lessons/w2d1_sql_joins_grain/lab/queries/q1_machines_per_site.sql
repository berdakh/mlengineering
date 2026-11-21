-- grain: one row per site (all sites, including those without machines)
SELECT s.site_id,
       s.site_name,
       COUNT(m.machine_id)                                               AS n_machines,
       COUNT(CASE WHEN m.machine_id IS NOT NULL
                   AND m.decommissioned_date IS NULL THEN 1 END)         AS n_active
FROM sites AS s
LEFT JOIN machines AS m ON m.site_id = s.site_id
GROUP BY s.site_id, s.site_name;
