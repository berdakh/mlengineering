# Mutant: happy_path_tests_only

**The mistake.** The implementation is correct, but the tests only use scores far
from the threshold, events in the interior of the array, and default parameters.
No case sits on a boundary (`==` threshold, event at the last sample, length
exactly `min_samples`, gap exactly `merge_gap`).

**Why it is plausible.** These are the cases one draws on a whiteboard.

**Expected outcome.** Passes on the correct implementation; most injected bugs survive.
