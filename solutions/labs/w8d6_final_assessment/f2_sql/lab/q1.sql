-- q1: delivered 2025 fee per region; NULL region reported as 'UNKNOWN'
SELECT COALESCE(a.region, 'UNKNOWN')        AS region,
       COUNT(DISTINCT s.account_id)         AS n_shipping_accounts,
       ROUND(SUM(s.fee), 2)                 AS total_fee
FROM shipments AS s
JOIN accounts AS a ON a.account_id = s.account_id
WHERE s.status = 'delivered'
  AND s.ship_date >= '2025-01-01' AND s.ship_date < '2026-01-01'
GROUP BY COALESCE(a.region, 'UNKNOWN');
