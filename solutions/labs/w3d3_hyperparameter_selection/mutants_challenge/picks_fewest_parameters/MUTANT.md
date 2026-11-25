# Mutant: "prefer simpler models" taken to mean "ignore the scores"

Always returns the trial with the fewest parameters. Its dev mean is an honest estimate (nothing was
selected on it), so the bias check passes - but no selection happened, and the chosen trials are no
better than the average trial.

Rejected by: `test_the_choice_is_better_than_not_selecting` (and the test-look check).
