# Mutant: default_range_frame

`q3` orders by `ts_epoch` only and gives no frame. With an `ORDER BY` and no frame the default is
`RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`, and under RANGE the "current row" includes all
its peers (rows with the same `ts_epoch`). A reading and its re-sent copy therefore both receive the
total including each other, so the first copy's running count is too high whenever the second copy
is flagged. The query runs, returns the right number of rows and is right for almost every row.

Changed file: `queries/q3_running_alerts.sql`
