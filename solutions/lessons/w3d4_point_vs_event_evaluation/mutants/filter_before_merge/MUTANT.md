# Mutant: duration filter applied before merging

`extract_events` drops short runs first and merges afterwards.

**Why it is plausible.** Both orders read naturally, and they agree whenever the fragments are long.

**What goes wrong.** A chattering alarm made of many 1-row bursts is deleted entirely instead of being
consolidated into one alarm, so a real detection disappears.

**Caught by.** `test_extract_events.py::test_merging_happens_before_the_duration_filter`.
