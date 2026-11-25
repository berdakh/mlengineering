WITH ranked AS (
    SELECT device_id, status, ts,
           RANK() OVER (PARTITION BY device_id ORDER BY ts_epoch DESC) AS rk
    FROM device_status_events
)
SELECT device_id, status, ts
FROM ranked
WHERE rk = 1;
