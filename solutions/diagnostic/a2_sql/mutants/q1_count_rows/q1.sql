SELECT COALESCE(c.country, 'UNKNOWN') AS country, COUNT(*) AS n_paying_customers, ROUND(SUM(i.amount), 2) AS revenue
FROM invoices AS i JOIN customers AS c ON c.customer_id = i.customer_id
WHERE i.status = 'paid' AND i.invoice_date >= '2025-01-01' AND i.invoice_date < '2026-01-01'
GROUP BY COALESCE(c.country, 'UNKNOWN');
