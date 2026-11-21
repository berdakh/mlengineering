SELECT customer_id FROM customers
WHERE signup_date >= '2025-01-01' AND signup_date < '2026-01-01'
  AND customer_id NOT IN (SELECT customer_id FROM tickets);
