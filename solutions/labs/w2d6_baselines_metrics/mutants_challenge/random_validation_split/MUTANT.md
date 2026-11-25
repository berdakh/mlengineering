# random_validation_split

Validation rows are a random 25% of the training rows instead of the last two snapshot months.

Why it is plausible: it is `train_test_split`, and the function still returns two frames of the right sizes.

Why it is wrong: the test set is later in time than the training set, and the same customers appear in many monthly snapshots. A random split validates on months the model was fitted on and on customers it has seen, so it cannot reveal calibration drift over time, which is exactly what happens on the test months here.

Caught by: `test_validation_months_come_after_all_fit_months`, `test_validation_block_was_computed_without_the_validation_labels_in_the_fit`.
