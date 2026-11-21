-- WRONG: counts invoice rows, not customers. A failed charge retried the same day is two rows for one customer,
-- so n_billed is inflated. (n_paid happens to be right here only because no customer has two paid invoices in a month.)
SELECT
    substr(i.invoice_date, 1, 7) AS month,
    COUNT(*)                     AS n_billed,
    SUM(i.status = 'paid')       AS n_paid,
    SUM(i.status = 'paid' AND EXISTS (
        SELECT 1 FROM invoices AS p
        WHERE p.customer_id = i.customer_id AND p.status = 'paid'
          AND substr(p.invoice_date, 1, 7) = strftime('%Y-%m', date(i.invoice_date, 'start of month', '-1 month'))
    ))                           AS n_retained
FROM invoices AS i
WHERE i.invoice_date >= '2025-01-01' AND i.invoice_date < '2026-01-01'
GROUP BY month ORDER BY month;
