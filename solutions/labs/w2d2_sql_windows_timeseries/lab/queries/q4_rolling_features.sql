-- Time-based 30-minute window (RANGE over epoch seconds), plus change and gap to the previous reading.
-- Grain: one row per de-duplicated reading.
SELECT reading_id, device_id, ts,
       AVG(temperature) OVER w30                   AS temp_mean_30m,
       COUNT(*)         OVER w30                   AS n_30m,
       temperature - LAG(temperature) OVER seq     AS delta_prev,
       ts_epoch    - LAG(ts_epoch)    OVER seq     AS gap_s
FROM readings_dedup
WINDOW
    seq AS (PARTITION BY device_id ORDER BY ts_epoch),
    w30 AS (PARTITION BY device_id ORDER BY ts_epoch RANGE BETWEEN 1800 PRECEDING AND CURRENT ROW);
