# Mutant: temporal split without the label delay

Train = everything issued before the cutoff. About 1,200 of those invoices have a `late` value that
was decided after 2024-10-01 (late means unpaid 30 days after the due date). The split is temporal in
issue date and still uses future information in the labels. On this table the metric barely moves
(test AUC 0.763 with the delay respected, 0.764 without), which is the instructive part: the check is on the construction, because
the size of this leak depends on how fast the world is changing.

Rejected by `test_training_labels_were_known_before_the_test_period` and `test_run_reports_sizes_and_prevalence`.
