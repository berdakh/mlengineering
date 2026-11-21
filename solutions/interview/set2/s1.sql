-- grain: one row per (ticket category, customer plan), with 'anonymous' standing in for tickets that have no customer
SELECT
    t.category,
    COALESCE(c.plan, 'anonymous')                                              AS plan,
    COUNT(*)                                                                   AS n_tickets,
    SUM(t.resolved_at IS NULL)                                                 AS n_open,
    ROUND(AVG((julianday(t.resolved_at) - julianday(t.opened_at)) * 24.0), 1)  AS avg_resolution_hours
FROM tickets AS t
LEFT JOIN customers AS c ON c.customer_id = t.customer_id   -- LEFT: anonymous tickets must survive the join
GROUP BY t.category, COALESCE(c.plan, 'anonymous');
