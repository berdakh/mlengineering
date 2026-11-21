# Mutant: asof_uses_latest_calibration

`q6` joins every reading to the device's *current* (most recent) calibration row instead of the row
in force at the reading's timestamp. Old readings are corrected with offsets that did not exist yet:
the query looks into the future. This is the most common point-in-time error in practice, because
dimension tables are usually queried "as of now". It also fills in values for readings taken before
the first calibration, which should stay NULL.

Changed file: `queries/q6_asof_calibration.sql`
