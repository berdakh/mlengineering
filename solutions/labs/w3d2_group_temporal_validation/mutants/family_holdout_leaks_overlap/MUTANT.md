# Mutant `family_holdout_leaks_overlap`

**Mistake.** `leave_one_family_out` accepts `keep_together` and ignores it, so an experiment that shares identical rows with a held-out experiment stays in training.

**Why plausible.** The family rule looks sufficient: "nothing of the held-out family is in training". Overlap groups cut across that rule, and in SKAB the reference recording and `other/5` show that shared rows do cross family boundaries.

**Caught by.** `test_family_holdout_drops_training_experiments_that_overlap_the_held_out_family`.
