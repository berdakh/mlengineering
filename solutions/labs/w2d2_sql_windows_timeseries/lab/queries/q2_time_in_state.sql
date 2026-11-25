-- Seconds spent in each status per device. An event lasts until the device's next event;
-- the last one lasts until the report end. Grain: one row per (device, status).
WITH intervals AS (
    SELECT device_id, status, ts_epoch AS start_epoch,
           LEAD(ts_epoch, 1, CAST(strftime('%s', '2026-03-04 00:00:00') AS INTEGER))
               OVER (PARTITION BY device_id ORDER BY ts_epoch, event_id) AS end_epoch
    FROM device_status_events
)
SELECT device_id, status, SUM(end_epoch - start_epoch) AS total_seconds
FROM intervals
GROUP BY device_id, status;
