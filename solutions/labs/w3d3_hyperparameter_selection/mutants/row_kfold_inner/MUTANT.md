# Mutant: inner folds are row-wise, not grouped

`grouped_search` takes the number of folds from `folds` but splits the *rows* into that many
interleaved parts. Every experiment is then on both sides of every inner split, so the search rewards
candidates that memorise experiment-specific structure - the same error as a row-level test split,
moved one level down where it is easier to miss.

Rejected by: the oracle comparison and the grouping tests in `checks/test_search.py`, and by
`checks/test_nested.py`.
