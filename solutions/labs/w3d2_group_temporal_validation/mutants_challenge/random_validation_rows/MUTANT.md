# Mutant `random_validation_rows`

**Mistake.** Validation rows are a random 20 % of the rows not used for training, from any week.

**Why plausible.** A random hold-out is the default reflex and is larger than eight weeks of data. It answers no deployment question here: it mixes weeks far beyond the use period and gives the 8-week retraining cycle no role.

**Caught by.** `test_validation_is_the_use_period_that_follows_the_cutoff`.
