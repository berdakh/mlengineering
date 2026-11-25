# pr_auc_from_hard_labels

`pr_auc` binarises the scores (here at their median) before building the curve.

Why it is plausible: passing `model.predict(X)` instead of `predict_proba` / `decision_function` to a ranking metric is one of the most common metric bugs; nothing crashes.

Why it is wrong: the curve then has a single operating point; the 'area' no longer summarises the ranking and depends on an arbitrary threshold.

Caught by: `test_pr_auc_matches_average_precision_including_ties`, `test_pr_auc_depends_only_on_the_ranking`.
