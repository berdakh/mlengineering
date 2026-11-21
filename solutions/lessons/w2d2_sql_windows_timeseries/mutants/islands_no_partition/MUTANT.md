# Mutant: islands_no_partition

In `q5` the `LAG(alert)` that detects the start of a run has no `PARTITION BY device_id`. "Previous
row" is then the previous reading of *any* device in global time order. A run on one device is cut
whenever another device's quiet reading is interleaved, and a new run fails to start when the
neighbouring device happens to be in alert. The result has plausible-looking episodes with wrong
boundaries and counts. The same mistake in pandas is `df.alert.shift()` without `groupby("device_id")`;
in EEG terms, it is running event extraction across concatenated channels.

Changed file: `queries/q5_alert_episodes.sql`
