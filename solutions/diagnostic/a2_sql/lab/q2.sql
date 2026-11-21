-- q2: 2025 signups that never opened a ticket.
-- NOT EXISTS is NULL-safe. `NOT IN (SELECT customer_id FROM tickets)` returns no rows at all here,
-- because tickets.customer_id contains NULLs and `x NOT IN (..., NULL)` is never TRUE.
SELECT c.customer_id
FROM customers AS c
WHERE c.signup_date >= '2025-01-01' AND c.signup_date < '2026-01-01'
  AND NOT EXISTS (SELECT 1 FROM tickets AS t WHERE t.customer_id = c.customer_id);
