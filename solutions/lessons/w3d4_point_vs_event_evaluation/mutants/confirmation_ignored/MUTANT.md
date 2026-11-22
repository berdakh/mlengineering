# Mutant: delay measured to the alarm's first row, whatever the persistence requirement

`detection_delay` ignores `confirm_rows`, so a 60-row minimum duration costs nothing in delay.

**Why it is plausible.** Offline, the alarm interval is known in full, and its start is the obvious
timestamp to use. The filter looks free.

**What goes wrong.** The reported delay is one the operator can never experience: an alarm that must
persist for 60 rows is announced 59 rows after it starts. Tuning `min_duration` on a delay that
ignores it always favours the longest filter.

**Caught by.** `test_time.py` (confirmation rows, pooled delay with `min_duration`).
