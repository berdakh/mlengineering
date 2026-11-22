# Mutant: outer fold takes part in the inner search

`nested_estimate` runs the search on **all** folds, then scores the winner on each fold in turn
("tune once with CV, then cross-validate the tuned model"). This is the most common way nested
validation is got wrong: the loop structure looks nested, but each outer fold has already voted for
the model that is scored on it.

Rejected by: the oracle comparison, the poisoned-fold test, the scoring-count test and the
pure-noise optimism test in `checks/test_nested.py`.
