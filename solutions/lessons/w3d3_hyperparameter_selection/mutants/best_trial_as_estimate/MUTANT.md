# Mutant: the winner's search score is reported as the estimate

The nested loop is correct, but `mean` is the average of the inner-search scores of the selected
candidates rather than of their scores on the untouched outer folds. The number reported is the
maximum of K noisy estimates: optimistic by construction.

Rejected by: `test_result_has_the_documented_fields` and the pure-noise optimism test.
