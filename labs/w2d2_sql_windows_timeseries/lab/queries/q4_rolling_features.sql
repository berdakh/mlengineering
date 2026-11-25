-- q4  Rolling features on an irregular time grid
--
-- Source : readings_dedup  (view: one row per device and timestamp)
-- Grain  : one row per de-duplicated reading
-- Columns: reading_id, device_id, ts, temp_mean_30m, n_30m, delta_prev, gap_s
-- Rules  : temp_mean_30m = mean temperature of this device's readings whose time lies in
--                          [t - 1800 s, t], both ends included, t = this reading's ts_epoch
--          n_30m         = number of readings in that same window (always >= 1)
--          delta_prev    = temperature minus the device's previous reading's temperature (NULL for the first)
--          gap_s         = seconds since the device's previous reading (NULL for the first)

SELECT NULL AS reading_id, NULL AS device_id, NULL AS ts, NULL AS temp_mean_30m,
       NULL AS n_30m, NULL AS delta_prev, NULL AS gap_s WHERE 0;
