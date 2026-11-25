-- As-of join: each reading gets the calibration row in force at its timestamp
-- (latest valid_from <= ts). Readings before a device's first calibration keep NULLs.
-- Grain: one row per de-duplicated reading.
WITH matched AS (
    SELECT r.reading_id, r.device_id, r.ts, r.temperature,
           c.offset_c, c.alert_threshold_c,
           ROW_NUMBER() OVER (PARTITION BY r.reading_id ORDER BY c.valid_from_epoch DESC) AS rn
    FROM readings_dedup AS r
    JOIN calibration AS c
           ON c.device_id = r.device_id
          AND c.valid_from_epoch <= r.ts_epoch
)
SELECT reading_id, device_id, ts,
       temperature + offset_c                       AS corrected_temperature,
       alert_threshold_c,
       temperature + offset_c > alert_threshold_c   AS over_threshold
FROM matched
WHERE rn = 1;
