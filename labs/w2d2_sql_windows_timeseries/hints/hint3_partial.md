# Hint 3 — partial implementation

The skeleton below is complete for the reading-based features and leaves the two status features
to you. The comments mark where point-in-time correctness is decided.

```sql
WITH reading_window AS (              -- grain: one row per label
    SELECT l.label_id,
           AVG(CASE WHEN r.ts_epoch > l.label_ts_epoch - 3600 THEN r.temperature END) AS mean_temp_60m,
           COALESCE(SUM(r.alert), 0)                                                  AS n_alerts_24h
    FROM maintenance_labels AS l
    LEFT JOIN readings_dedup AS r
           ON r.device_id = l.device_id
          AND r.ts_epoch <= l.label_ts_epoch            -- nothing after the label
          AND r.ts_epoch >  l.label_ts_epoch - 86400
    GROUP BY l.label_id
),
last_reading AS (                     -- grain: one row per label that has any earlier reading
    SELECT label_id, temperature AS last_temperature
    FROM (
        SELECT l.label_id, r.temperature,
               ROW_NUMBER() OVER (PARTITION BY l.label_id ORDER BY r.ts_epoch DESC) AS rn
        FROM maintenance_labels AS l
        JOIN readings_dedup AS r
          ON r.device_id = l.device_id
         AND r.ts_epoch <= l.label_ts_epoch             -- nothing after the label
    )
    WHERE rn = 1
),
past_events AS (                      -- grain: one row per (label, status event at or before it)
    SELECT l.label_id, l.label_ts_epoch, e.status, e.ts_epoch,
           ROW_NUMBER() OVER (PARTITION BY l.label_id ORDER BY /* latest first, total order */) AS rn
    FROM maintenance_labels AS l
    JOIN device_status_events AS e
      ON e.device_id = l.device_id
     AND /* time bound */
)
-- TODO: status_now  (label_id, status_at_label)      from past_events
-- TODO: last_fault  (label_id, seconds_since_fault)  from past_events
SELECT l.label_id, l.failed,
       lr.last_temperature, rw.mean_temp_60m, rw.n_alerts_24h
       -- , seconds_since_fault, status_at_label
FROM maintenance_labels AS l
LEFT JOIN reading_window AS rw ON rw.label_id = l.label_id
LEFT JOIN last_reading   AS lr ON lr.label_id = l.label_id;
```

Why `last_reading` may use an inner join while `reading_window` may not: `last_reading` is
left-joined to the labels in the final select, so a label without readings still appears;
`reading_window` computes a count that must be 0 rather than missing, so the label has to survive
inside the CTE.
