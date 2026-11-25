-- q1  Latest status per device
--
-- Source : device_status_events
-- Grain  : one row per device (6 rows)
-- Columns: device_id, status, ts
-- Rule   : "latest" = greatest ts_epoch; when two events share a timestamp, the one
--          logged later (greater event_id) is the latest.
--
-- Write ONE statement (a WITH ... SELECT counts as one). Replace the placeholder below.

SELECT NULL AS device_id, NULL AS status, NULL AS ts WHERE 0;
