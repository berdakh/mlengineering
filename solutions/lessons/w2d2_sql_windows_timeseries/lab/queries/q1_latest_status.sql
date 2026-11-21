-- Latest status per device. Ties on ts are broken by log order (event_id).
-- Grain: one row per device.
WITH ranked AS (
    SELECT device_id, status, ts,
           ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY ts_epoch DESC, event_id DESC) AS rn
    FROM device_status_events
)
SELECT device_id, status, ts
FROM ranked
WHERE rn = 1;
