-- q2  Time in state
--
-- Source : device_status_events
-- Grain  : one row per (device_id, status) that occurs in the device's log
-- Columns: device_id, status, total_seconds
-- Rule   : an event's state lasts until the same device's next event (order: ts_epoch, event_id).
--          The last event of each device lasts until the report end, 2026-03-04 00:00:00 UTC
--          (epoch 1772582400). A zero-length state still counts as a row with 0 seconds.

SELECT NULL AS device_id, NULL AS status, NULL AS total_seconds WHERE 0;
