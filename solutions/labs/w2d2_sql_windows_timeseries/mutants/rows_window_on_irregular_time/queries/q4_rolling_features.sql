SELECT reading_id, device_id, ts,
       AVG(temperature) OVER w30                   AS temp_mean_30m,
       COUNT(*)         OVER w30                   AS n_30m,
       temperature - LAG(temperature) OVER seq     AS delta_prev,
       ts_epoch    - LAG(ts_epoch)    OVER seq     AS gap_s
FROM readings_dedup
WINDOW
    seq AS (PARTITION BY device_id ORDER BY ts_epoch),
    w30 AS (PARTITION BY device_id ORDER BY ts_epoch ROWS BETWEEN 6 PRECEDING AND CURRENT ROW);
