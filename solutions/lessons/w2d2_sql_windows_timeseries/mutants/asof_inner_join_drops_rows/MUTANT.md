# Mutant: asof_inner_join_drops_rows

The as-of logic in `q6` is right, but the join is an inner join. Readings taken before a device's
first calibration have no matching row and disappear, so the result no longer has one row per
reading. Downstream, a model would silently be trained without the earliest period of that device.

Changed file: `queries/q6_asof_calibration.sql`
