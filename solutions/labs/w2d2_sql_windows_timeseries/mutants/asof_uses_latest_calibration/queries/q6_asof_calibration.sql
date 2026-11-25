WITH current_cal AS (
    SELECT device_id, offset_c, alert_threshold_c
    FROM (
        SELECT c.*, ROW_NUMBER() OVER (PARTITION BY device_id ORDER BY valid_from_epoch DESC) AS rn
        FROM calibration AS c
    )
    WHERE rn = 1
)
SELECT r.reading_id, r.device_id, r.ts,
       r.temperature + c.offset_c                         AS corrected_temperature,
       c.alert_threshold_c,
       r.temperature + c.offset_c > c.alert_threshold_c   AS over_threshold
FROM readings_dedup AS r
LEFT JOIN current_cal AS c ON c.device_id = r.device_id;
