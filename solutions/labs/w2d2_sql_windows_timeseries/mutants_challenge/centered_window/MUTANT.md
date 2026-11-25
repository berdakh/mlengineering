# Mutant: centered_window

`mean_temp_60m` averages readings within 60 minutes on *either side* of the label
(`ABS(ts - label_ts) <= 3600`), the habit of someone used to centred windows in offline signal
analysis. The hour after a failing inspection is exactly where the temperature rises, so this single
feature separates the classes almost perfectly offline and is unavailable at prediction time.
Rejected by the future-invariance check and by the comparison with the specification.

Changed file: `features.sql`
