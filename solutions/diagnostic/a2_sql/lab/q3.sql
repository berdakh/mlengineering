-- q3: per premium customer, total paid amount and number of tickets.
-- Aggregate each child table to one row per customer BEFORE joining. Joining invoices and tickets
-- to customers in one step yields (#invoices x #tickets) rows per customer and inflates both figures.
WITH paid AS (
    SELECT customer_id, SUM(amount) AS total_paid
    FROM invoices WHERE status = 'paid' GROUP BY customer_id
),
tk AS (
    SELECT customer_id, COUNT(*) AS n_tickets
    FROM tickets WHERE customer_id IS NOT NULL GROUP BY customer_id
)
SELECT c.customer_id,
       ROUND(COALESCE(paid.total_paid, 0), 2) AS total_paid,
       COALESCE(tk.n_tickets, 0)              AS n_tickets
FROM customers AS c
LEFT JOIN paid ON paid.customer_id = c.customer_id
LEFT JOIN tk   ON tk.customer_id = c.customer_id
WHERE c.plan = 'premium';
