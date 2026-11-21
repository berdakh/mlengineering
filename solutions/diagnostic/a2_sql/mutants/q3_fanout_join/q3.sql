SELECT c.customer_id,
       ROUND(COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.amount END), 0), 2) AS total_paid,
       COUNT(t.ticket_id) AS n_tickets
FROM customers AS c
LEFT JOIN invoices AS i ON i.customer_id = c.customer_id
LEFT JOIN tickets AS t ON t.customer_id = c.customer_id
WHERE c.plan = 'premium'
GROUP BY c.customer_id;
