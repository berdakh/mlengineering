SELECT a.account_id,
       ROUND(COALESCE(SUM(CASE WHEN s.status = 'delivered' THEN s.fee END), 0), 2),
       COUNT(DISTINCT c.complaint_id)
FROM accounts AS a
LEFT JOIN shipments AS s ON s.account_id = a.account_id
LEFT JOIN complaints AS c ON c.account_id = a.account_id
WHERE a.tier = 'enterprise'
GROUP BY a.account_id;
