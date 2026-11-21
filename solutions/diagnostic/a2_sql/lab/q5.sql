-- q5: monthly paid revenue in 2025 and change versus the previous month
WITH monthly AS (
    SELECT substr(invoice_date, 1, 7) AS month, SUM(amount) AS revenue
    FROM invoices
    WHERE status = 'paid' AND invoice_date >= '2025-01-01' AND invoice_date < '2026-01-01'
    GROUP BY substr(invoice_date, 1, 7)
)
SELECT month,
       ROUND(revenue, 2)                                      AS revenue,
       ROUND(revenue - LAG(revenue) OVER (ORDER BY month), 2) AS change_vs_prev
FROM monthly
ORDER BY month;
