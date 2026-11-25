# Mutant: the training set is "everything except the validation fold"

`train = ~held_out` looks equivalent to "the other folds", and is equivalent only when the table
contains nothing but development experiments. Here the table also holds the test experiments (and,
on SKAB, the reference recording), so every model in the search - and every refit in the nested
estimate - is trained on test rows.

Rejected by: `test_rows_outside_the_folds_are_never_fitted_or_scored` in `checks/test_search.py`.
