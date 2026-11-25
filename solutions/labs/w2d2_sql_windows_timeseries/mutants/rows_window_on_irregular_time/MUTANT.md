# Mutant: rows_window_on_irregular_time

`q4` approximates "the last 30 minutes" by "the last 7 rows" because the nominal cadence is 5 minutes.
With dropped samples and outages, 7 rows can span hours; with jitter they can span less than 30
minutes. A `ROWS` frame counts rows, a `RANGE` frame with an offset measures the ORDER BY value.
The pandas version of the same mistake is `rolling(7)` instead of `rolling("1800s")`.

Changed file: `queries/q4_rolling_features.sql`
