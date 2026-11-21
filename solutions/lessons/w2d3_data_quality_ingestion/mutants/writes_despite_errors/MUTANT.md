# Mutant: writes_despite_errors

Error-severity failures are printed as a warning; the table is written anyway and the command exits 0.

Why it is plausible: "the report is there if anyone wants to look", and stopping feels obstructive
while developing. Why it is wrong: every downstream step, scheduler and CI job reads the exit code and
the presence of the file, not the prose. A pipeline that cannot fail cannot protect anything; the
duplicate rows flow into features and the first symptom is a metric nobody can explain.

Rejected by: `test_errors_stop_the_pipeline_loudly`, `test_no_stale_table_survives_a_failed_rerun`.
