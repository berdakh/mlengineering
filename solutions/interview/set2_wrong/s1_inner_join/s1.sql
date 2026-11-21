-- WRONG: the inner join silently drops the 60 tickets that have no customer_id, so the 'anonymous' groups vanish.
SELECT t.category, c.plan, COUNT(*), SUM(t.resolved_at IS NULL),
       ROUND(AVG((julianday(t.resolved_at) - julianday(t.opened_at)) * 24.0), 1)
FROM tickets AS t
JOIN customers AS c ON c.customer_id = t.customer_id
GROUP BY t.category, c.plan;
