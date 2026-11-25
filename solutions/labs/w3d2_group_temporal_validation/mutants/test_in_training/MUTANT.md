# Mutant `test_in_training`

**Mistake.** `grouped_folds` does not check that the development folds are disjoint from the test and reference experiments.

**Why plausible.** A manifest edited by hand, or regenerated with a different seed while an old test list is pasted back, is exactly how a test experiment ends up in a development fold. Without this guard every tuning decision is then made with test data.

**Caught by.** `test_grouped_folds_reject_a_test_experiment_among_the_folds`.
