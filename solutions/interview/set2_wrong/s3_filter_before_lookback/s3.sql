-- WRONG: restricts to 2025 before looking back, so January 2025 has no previous month and n_retained = 0 there.
WITH customer_month AS (
    SELECT customer_id, substr(invoice_date, 1, 7) AS month, MAX(status = 'paid') AS paid
    FROM invoices
    WHERE invoice_date >= '2025-01-01' AND invoice_date < '2026-01-01'
    GROUP BY customer_id, substr(invoice_date, 1, 7)
),
flagged AS (
    SELECT cm.*, EXISTS (
        SELECT 1 FROM customer_month AS prev
        WHERE prev.customer_id = cm.customer_id AND prev.paid = 1
          AND prev.month = strftime('%Y-%m', date(cm.month || '-01', '-1 month'))) AS paid_prev
    FROM customer_month AS cm
)
SELECT month, COUNT(*), SUM(paid), SUM(paid = 1 AND paid_prev = 1)
FROM flagged GROUP BY month ORDER BY month;
