SELECT COALESCE(a.region, 'UNKNOWN'), COUNT(*), ROUND(SUM(s.fee), 2)
FROM shipments AS s JOIN accounts AS a ON a.account_id = s.account_id
WHERE s.status = 'delivered' AND s.ship_date >= '2025-01-01' AND s.ship_date < '2026-01-01'
GROUP BY COALESCE(a.region, 'UNKNOWN');
