# Mutant: top1_with_ties

`q1` uses `RANK() ... ORDER BY ts_epoch DESC` and keeps rank 1. Two log lines with the same timestamp
both get rank 1, so the device appears twice with two different "latest" statuses and every downstream
join on `device_id` fans out. The same failure occurs with `WHERE ts = (SELECT MAX(ts) ...)`.
The fix is a total order: `ROW_NUMBER()` with a tie-breaker (`event_id`).

Changed file: `queries/q1_latest_status.sql`
