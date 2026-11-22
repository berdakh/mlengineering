# Mutant: identical rows dominate each other

Uses >= on every objective without requiring a strict improvement on one, so two identical candidates
knock each other off the front. A plausible slip when writing dominance from memory. Caught by
`test_pareto_identical_rows_are_both_kept` and the known-answer test (B and D tie on AUC).
