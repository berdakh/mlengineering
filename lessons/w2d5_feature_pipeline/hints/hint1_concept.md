# Hint 1 — concept

**Lab.** Every failure in `test_causality.py` is an answer to one question: *which rows was
this feature allowed to read?* For row *i* the allowed set is: same experiment, same segment,
time ≤ time of row *i*. Before writing code, write that set down for three rows of the
synthetic frame: the first row of an experiment, the row just after the 90 s gap, and an
ordinary row in the middle. If your implementation can reach a row outside the set for any of
the three, a check will find it.

The reference-statistics checks ask a second question: *when was this number estimated, and on
what?* A z-score has two inputs, the value and the statistics. Only the value may come from the
frame being transformed.

The cache checks ask a third: *what would have to change for this table to be a different
table?* Each of those things belongs in the key.

**Challenge.** A row-count window answers "the last *n* readings". The task asks for "the
readings of the last *w* seconds". On irregular data these are different sets. Decide which
library primitive gives you the second, then find out which endpoint it includes.
