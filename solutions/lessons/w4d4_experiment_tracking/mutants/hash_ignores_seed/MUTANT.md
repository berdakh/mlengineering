# Mutant: the seed is left out of the run id

"The seed is not a hyperparameter, so it should not change the id." Then runs that differ only in
seed share one directory: the second seed is skipped as "already complete" and the table shows
n = 1 where you asked for three seeds. Caught by: identity, expansion and table checks.
