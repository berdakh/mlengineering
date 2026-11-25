WITH flagged AS (
    SELECT device_id, ts, ts_epoch, temperature, alert,
           CASE WHEN alert = 1 AND COALESCE(LAG(alert) OVER (ORDER BY ts_epoch), 0) = 0
                THEN 1 ELSE 0 END AS starts_episode
    FROM readings_dedup
),
numbered AS (
    SELECT *,
           SUM(starts_episode) OVER (
               PARTITION BY device_id ORDER BY ts_epoch
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
           ) AS episode_no
    FROM flagged
)
SELECT device_id, episode_no,
       MIN(ts) AS start_ts, MAX(ts) AS end_ts, COUNT(*) AS n_samples, MAX(temperature) AS peak_temperature
FROM numbered
WHERE alert = 1
GROUP BY device_id, episode_no;
