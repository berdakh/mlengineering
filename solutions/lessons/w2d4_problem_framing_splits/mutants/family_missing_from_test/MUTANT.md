# Mutant: family_missing_from_test

**The mistake.** A correct *grouped* split that ignores family: experiments are shuffled as one pool.
With a small family (`valve2` has 4 experiments in SKAB, 2 in the check data) some seeds leave it
out of the test set entirely, so the headline test metric silently says nothing about that fault type.

**Why a learner writes it.** Group-awareness is the lesson they already know; stratification of the
*groups* by a higher-level attribute is the step that is easy to forget. It also passes for most seeds.

**Caught by.** `test_test_set_is_stratified_by_family` (checked over ten seeds, not one).
