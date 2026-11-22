-- q5: monthly delivered fee in 2025 and change versus the previous month
WITH monthly AS (
    SELECT substr(ship_date, 1, 7) AS month, SUM(fee) AS total_fee
    FROM shipments
    WHERE status = 'delivered' AND ship_date >= '2025-01-01' AND ship_date < '2026-01-01'
    GROUP BY substr(ship_date, 1, 7)
)
SELECT month,
       ROUND(total_fee, 2)                                        AS total_fee,
       ROUND(total_fee - LAG(total_fee) OVER (ORDER BY month), 2) AS change_vs_prev
FROM monthly
ORDER BY month;
