-- q4: accounts whose most recent shipment was lost (latest date; ties -> highest shipment_id).
-- A lost parcel is often re-shipped the same day; the re-shipment has the higher id and is the latest.
WITH ranked AS (
    SELECT account_id, shipment_id, ship_date, status,
           ROW_NUMBER() OVER (PARTITION BY account_id
                              ORDER BY ship_date DESC, shipment_id DESC) AS rn
    FROM shipments
)
SELECT account_id, shipment_id, ship_date
FROM ranked
WHERE rn = 1 AND status = 'lost';
