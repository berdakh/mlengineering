-- WRONG: numbers ALL invoices and filters afterwards, so it returns "the third invoice, if it happens to be paid",
-- and the running total includes failed and refunded amounts.
WITH numbered AS (
    SELECT customer_id, invoice_id, invoice_date, status,
           ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY invoice_date, invoice_id) AS rn,
           SUM(amount)  OVER (PARTITION BY customer_id ORDER BY invoice_date, invoice_id) AS cumulative_paid
    FROM invoices
)
SELECT customer_id, invoice_id, invoice_date, ROUND(cumulative_paid, 2)
FROM numbered
WHERE rn = 3 AND status = 'paid';
