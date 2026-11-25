-- q5  Alert episodes (gaps and islands)
--
-- Source : readings_dedup
-- Grain  : one row per (device_id, episode)
-- Columns: device_id, episode_no, start_ts, end_ts, n_samples, peak_temperature
-- Rules  : an episode is a maximal run of consecutive readings of one device with alert = 1
--          ("consecutive" = adjacent in that device's time-ordered sequence).
--          episode_no counts a device's episodes 1, 2, 3, ... in time order.
--          start_ts / end_ts = ts of the first / last reading of the run.

SELECT NULL AS device_id, NULL AS episode_no, NULL AS start_ts, NULL AS end_ts,
       NULL AS n_samples, NULL AS peak_temperature WHERE 0;
