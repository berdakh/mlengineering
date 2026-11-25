# Mutant: unpaired resampling in the "paired" difference

Model A and model B are resampled with independent draws of clusters. The point estimate of the
difference is still right, but the replicate differences now contain the between-cluster difficulty
twice over instead of cancelling it, so the interval is as wide as for two unrelated test sets.

Why it is tempting: calling the one-sample bootstrap twice and subtracting looks equivalent.

Rejected by: `test_paired_interval_detects_a_small_consistent_difference`,
`test_paired_difference_of_identical_models_is_exactly_zero`.
