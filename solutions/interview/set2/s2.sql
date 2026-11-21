-- grain: one row per customer who has at least three paid invoices
WITH paid AS (
    SELECT
        customer_id, invoice_id, invoice_date,
        ROW_NUMBER() OVER w AS rn,
        SUM(amount)  OVER (w ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_paid
    FROM invoices
    WHERE status = 'paid'                       -- filter BEFORE numbering: we want the third PAID invoice
    WINDOW w AS (PARTITION BY customer_id ORDER BY invoice_date, invoice_id)
)
SELECT customer_id, invoice_id, invoice_date, ROUND(cumulative_paid, 2) AS cumulative_paid
FROM paid
WHERE rn = 3;
