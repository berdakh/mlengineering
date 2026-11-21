-- Point-in-time-correct features for each maintenance label.
-- Every source row is restricted to ts <= label_ts in the join condition itself.
-- Grain: one row per label.
WITH reading_window AS (
    SELECT l.label_id,
           AVG(CASE WHEN r.ts_epoch > l.label_ts_epoch - 3600 THEN r.temperature END) AS mean_temp_60m,
           COALESCE(SUM(r.alert), 0)                                                  AS n_alerts_24h
    FROM maintenance_labels AS l
    LEFT JOIN readings_dedup AS r
           ON r.device_id = l.device_id
          AND r.ts_epoch <= l.label_ts_epoch
          AND r.ts_epoch >  l.label_ts_epoch - 86400
    GROUP BY l.label_id
),
last_reading AS (
    SELECT label_id, temperature AS last_temperature
    FROM (
        SELECT l.label_id, r.temperature,
               ROW_NUMBER() OVER (PARTITION BY l.label_id ORDER BY r.ts_epoch DESC) AS rn
        FROM maintenance_labels AS l
        JOIN readings_dedup AS r
          ON r.device_id = l.device_id AND r.ts_epoch <= l.label_ts_epoch
    )
    WHERE rn = 1
),
past_events AS (
    SELECT l.label_id, l.label_ts_epoch, e.status, e.ts_epoch,
           ROW_NUMBER() OVER (PARTITION BY l.label_id ORDER BY e.ts_epoch DESC, e.event_id DESC) AS rn
    FROM maintenance_labels AS l
    JOIN device_status_events AS e
      ON e.device_id = l.device_id AND e.ts_epoch <= l.label_ts_epoch
),
status_now AS (
    SELECT label_id, status AS status_at_label FROM past_events WHERE rn = 1
),
last_fault AS (
    SELECT label_id, MIN(label_ts_epoch - ts_epoch) AS seconds_since_fault
    FROM past_events
    WHERE status = 'fault'
    GROUP BY label_id
)
SELECT l.label_id, l.failed,
       lr.last_temperature,
       rw.mean_temp_60m,
       rw.n_alerts_24h,
       lf.seconds_since_fault,
       sn.status_at_label
FROM maintenance_labels AS l
LEFT JOIN reading_window AS rw ON rw.label_id = l.label_id
LEFT JOIN last_reading   AS lr ON lr.label_id = l.label_id
LEFT JOIN status_now     AS sn ON sn.label_id = l.label_id
LEFT JOIN last_fault     AS lf ON lf.label_id = l.label_id;
