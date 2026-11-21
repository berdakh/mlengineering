-- Running count of alert-flagged rows per device in arrival-consistent order (ts, reading_id).
-- ROWS is explicit: the default frame (RANGE ... CURRENT ROW) would add tied rows to each other.
-- Grain: one row per raw reading.
SELECT reading_id, device_id,
       SUM(alert) OVER (
           PARTITION BY device_id
           ORDER BY ts_epoch, reading_id
           ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
       ) AS running_alerts
FROM sensor_readings;
