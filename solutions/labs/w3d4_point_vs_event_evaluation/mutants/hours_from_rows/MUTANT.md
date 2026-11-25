# Mutant: hours computed from the row count

`normal_hours` counts normal rows and divides by 3600, assuming one row per second.

**Why it is plausible.** SKAB's median sampling interval is 1 s, so the number is nearly right on the
project data and the shortcut goes unnoticed.

**What goes wrong.** At 2 s sampling the false-alarm rate is reported at twice its true value; a
logging gap silently disappears from the exposure; the function ignores `times` altogether.

**Caught by.** `test_time.py` (2 s and 10 s sampling, gap, false alarms per hour, pooled check).
