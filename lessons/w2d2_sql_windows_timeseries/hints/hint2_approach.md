# Hint 2 — suggested approach

Write one CTE per feature family, each keyed by `label_id`, then left-join them all back to
`maintenance_labels` at the end. Test each CTE on its own with `run_query.py --sql` before
combining; state its grain in a comment.

1. **`reading_window`** (grain: label). `maintenance_labels l LEFT JOIN readings_dedup r` on device
   and on `r.ts_epoch` in the trailing **24-hour** interval. Group by `l.label_id`.
   - `n_alerts_24h` is a sum over everything joined; wrap it in `COALESCE(..., 0)`.
   - `mean_temp_60m` is an average over the last hour only. A conditional aggregate does that
     without a second join: `AVG(CASE WHEN <within last hour> THEN r.temperature END)`. `AVG`
     ignores NULLs, and returns NULL when nothing qualifies, which is what the specification asks.
2. **`last_reading`** (grain: label). Join labels to readings at or before the label, number them
   per label by time descending, keep number 1. This is q6 from the lab with a different right side.
3. **`past_events`** (grain: label × past event). Join labels to status events at or before the
   label and number them per label, latest first, with `event_id` as tie-breaker. Two features
   read from it:
   - `status_at_label`: the row numbered 1.
   - `seconds_since_fault`: among rows with `status = 'fault'`, the smallest
     `label_ts_epoch - ts_epoch`.
4. **Final select** from `maintenance_labels` with four `LEFT JOIN`s on `label_id`.

Check the grain at the end: `SELECT COUNT(*), COUNT(DISTINCT label_id)` over your result must give
38 and 38.
