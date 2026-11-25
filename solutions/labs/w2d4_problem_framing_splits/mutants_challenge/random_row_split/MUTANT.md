# Mutant: random_row_split

**The mistake.** Labelled rows are split at random 60/20/20. Neither time nor customer is respected:
the same customer's adjacent months sit on both sides, and training rows post-date test rows.

**Why a learner writes it.** It is what `train_test_split` does, and on this kind of table it produces
flattering numbers.

**Caught by.** Almost every check, first `test_no_training_label_looks_into_the_test_period`.
