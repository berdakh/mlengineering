-- q3  Running count of flagged rows (ingest audit)
--
-- Source : sensor_readings  (the RAW table, re-sent rows included)
-- Grain  : one row per raw reading (4,811 rows in the shipped database)
-- Columns: reading_id, device_id, running_alerts
-- Rule   : running_alerts = number of rows with alert = 1 for this device, counted up to and
--          including this row, in the order (ts_epoch, reading_id).

SELECT NULL AS reading_id, NULL AS device_id, NULL AS running_alerts WHERE 0;
