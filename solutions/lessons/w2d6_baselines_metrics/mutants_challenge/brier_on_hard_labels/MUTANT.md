# brier_on_hard_labels

`brier_score` thresholds the probabilities at 0.5 first, which turns it into the error rate.

Why it is plausible: the same habit as passing `predict()` to a ranking metric; with 7% prevalence almost no probability exceeds 0.5, so the result looks like a sensible small number (the churn rate).

Why it is wrong: the score no longer rewards calibrated probabilities; a model and the prevalence forecast become indistinguishable.

Caught by: `test_brier_score_matches_definition`, `test_report_is_consistent_with_the_functions`.
