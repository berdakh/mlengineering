# Mutant: no_purge_gap

**The mistake.** "Train on everything before the test period." Rows from the three months before
`test_start` carry labels that describe the test period; at training time those outcomes had not
happened. This is the customer-data version of overlapping windows straddling a train/test boundary.

**Why a learner writes it.** It is the standard temporal split, and it is correct when the label
horizon is zero.

**Caught by.** `test_no_training_label_looks_into_the_test_period`, `test_horizon_controls_the_gap`.
