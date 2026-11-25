# Mutant: late_joiners_called_known

**The mistake.** "New" is defined as "sampled into the hold-out", "known" as everyone else. Customers
who signed up after the last trainable month are not in the hold-out sample, so they are reported as
known although the model never saw them. The `test_known` number is diluted with cold-start cases.

**Why a learner writes it.** The split is thought of as a property of the sampling step rather than of
what actually ended up in the training data.

**Caught by.** `test_known_and_new_mean_what_they_say`, `test_zero_fraction_holds_nobody_out_by_design`.
