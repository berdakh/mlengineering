-- q4: customers whose most recent invoice failed (latest date; ties -> highest invoice_id)
WITH ranked AS (
    SELECT customer_id, invoice_id, invoice_date, status,
           ROW_NUMBER() OVER (PARTITION BY customer_id
                              ORDER BY invoice_date DESC, invoice_id DESC) AS rn
    FROM invoices
)
SELECT customer_id, invoice_id, invoice_date
FROM ranked
WHERE rn = 1 AND status = 'failed';
