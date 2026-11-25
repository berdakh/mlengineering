# Mutant: dropna_loses_normal

The notebook's "clean up" cell (`all_df = all_df.dropna()`) was moved into `load_raw` unchanged. The
fault-free recording has no label columns, so after concatenation its labels are NaN and `dropna()`
deletes all of it: 9,405 of 46,806 real rows, the only reference data for semi-supervised detectors,
with no error and a plausible-looking row count (37,401 is the number of *labelled* rows).

The learner then wrote tests that describe what the code does (4 experiments) instead of what it should do.
Rejected by `test_file_without_labels_is_kept_as_normal`, `test_no_experiment_is_lost`,
`test_experiment_ids_come_from_file_names`, `test_summary_command`.
