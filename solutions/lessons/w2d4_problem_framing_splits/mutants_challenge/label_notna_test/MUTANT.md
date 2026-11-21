# Mutant: label_notna_test

**The mistake.** Test rows are "everything from `test_start` with a label". In the last snapshots the
only known labels are early cancellations, so the test set gains rows that are all positives
(censoring). On the supplied file the churn rate becomes 0.199 instead of 0.163.

**Why a learner writes it.** `dropna()` on the target is the most automatic line in pandas.

**Caught by.** `test_test_rows_are_chosen_by_calendar_not_by_label_availability`,
`test_every_evaluable_row_is_evaluated_exactly_once`.
