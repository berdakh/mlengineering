-- grain: one row per site (all sites)
-- key: site_id
-- Three independent one-to-many branches hang off a site. Each is reduced to one row per site
-- in its own CTE; only then are they joined.
WITH machine_counts AS (
    SELECT site_id, COUNT(*) AS n_machines FROM machines GROUP BY site_id
),
downtime AS (
    SELECT m.site_id, SUM(d.hours) AS downtime_hours
    FROM downtime_events AS d
    JOIN machines AS m ON m.machine_id = d.machine_id
    GROUP BY m.site_id
),
labor AS (
    SELECT m.site_id, SUM(w.labor_hours) AS labor_hours
    FROM work_orders AS w
    JOIN machines AS m ON m.machine_id = w.machine_id
    GROUP BY m.site_id
),
parts_cost AS (
    SELECT m.site_id, SUM(pu.quantity * p.unit_cost) AS parts_cost
    FROM parts_used AS pu
    JOIN parts AS p       ON p.part_id = pu.part_id
    JOIN work_orders AS w ON w.wo_id = pu.wo_id
    JOIN machines AS m    ON m.machine_id = w.machine_id
    GROUP BY m.site_id
)
SELECT s.site_id,
       COALESCE(mc.n_machines, 0)       AS n_machines,
       COALESCE(dt.downtime_hours, 0.0) AS downtime_hours,
       COALESCE(lb.labor_hours, 0.0)    AS labor_hours,
       COALESCE(pc.parts_cost, 0.0)     AS parts_cost
FROM sites AS s
LEFT JOIN machine_counts AS mc ON mc.site_id = s.site_id
LEFT JOIN downtime AS dt       ON dt.site_id = s.site_id
LEFT JOIN labor AS lb          ON lb.site_id = s.site_id
LEFT JOIN parts_cost AS pc     ON pc.site_id = s.site_id;
