# Mutant: heldout_history_in_train

**The mistake.** Customers are designated "new" for the test period, but their earlier snapshots stay
in the training data. `test_new` then measures performance on customers the model has seen.

**Why a learner writes it.** The hold-out is applied where the test set is built, and the training
filter is written separately as a pure date filter.

**Caught by.** `test_known_and_new_mean_what_they_say`, `test_requested_fraction_of_customers_is_held_out`.
