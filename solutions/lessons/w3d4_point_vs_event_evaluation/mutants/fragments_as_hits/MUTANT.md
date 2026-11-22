# Mutant: every fragment is a true positive

Each alarm that starts inside a true event is labelled `"hit"`, so a chattering detector that
announces one fault twenty times collects twenty true positives.

**Why it is plausible.** It is what point-wise thinking suggests: each alarm overlaps a true event,
so each is "correct".

**What goes wrong.** Event precision is inflated by chatter: 1 false alarm + 1 fault announced four
times scores precision 0.8 instead of 0.5. The noisier the alarm stream, the better it looks.

**Caught by.** `test_matching.py` (fragmented detection, redundant alarms, mixed case) and the pooled check.
