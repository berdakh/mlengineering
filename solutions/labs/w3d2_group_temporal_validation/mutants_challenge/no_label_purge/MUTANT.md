# Mutant `no_label_purge`

**Mistake.** Training uses every labelled row with `week <= cutoff`. The labels of the last four training weeks sum demand from weeks *after* the cut-off.

**Why plausible.** "Train on the past, validate on the future" sounds complete when stated in terms of the row's own week. The label's look-ahead window is what crosses the boundary: at the cut-off those labels did not exist yet, and they share up to three of four weeks with the first validation labels.

**Caught by.** `test_training_uses_only_labels_fully_observed_at_the_cutoff`, `test_training_keeps_everything_that_was_available`, and the planted-shock check (correlation about 0.5 instead of about 0).
