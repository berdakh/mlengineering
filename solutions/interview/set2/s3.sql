-- grain: one row per calendar month of 2025
WITH customer_month AS (            -- first reduce to one row per (customer, month): removes retry fan-out
    SELECT
        customer_id,
        substr(invoice_date, 1, 7)            AS month,
        MAX(status = 'paid')                  AS paid
    FROM invoices
    GROUP BY customer_id, substr(invoice_date, 1, 7)
),
flagged AS (                        -- look back BEFORE restricting to 2025, so January sees December 2024
    SELECT
        cm.customer_id, cm.month, cm.paid,
        EXISTS (
            SELECT 1 FROM customer_month AS prev
            WHERE prev.customer_id = cm.customer_id
              AND prev.paid = 1
              AND prev.month = strftime('%Y-%m', date(cm.month || '-01', '-1 month'))
        ) AS paid_prev
    FROM customer_month AS cm
)
SELECT
    month,
    COUNT(*)                                   AS n_billed,
    SUM(paid)                                  AS n_paid,
    SUM(paid = 1 AND paid_prev = 1)            AS n_retained
FROM flagged
WHERE month BETWEEN '2025-01' AND '2025-12'
GROUP BY month
ORDER BY month;
