SELECT s.account_id, s.shipment_id, s.ship_date
FROM shipments AS s
JOIN (SELECT account_id, MAX(ship_date) AS d FROM shipments GROUP BY account_id) AS m
  ON m.account_id = s.account_id AND m.d = s.ship_date
WHERE s.status = 'lost';
