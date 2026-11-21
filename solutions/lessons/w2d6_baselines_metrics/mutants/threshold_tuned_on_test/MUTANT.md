# threshold_tuned_on_test

The decision threshold is chosen to maximise F1 on the **test** experiments, then reported on the same rows.

Why it is plausible: `best_f1_threshold(y, scores)` is the natural call when you hold one evaluation set, and published SKAB leaderboards have been criticised for evaluating on data used for tuning.

Why it is wrong: the reported precision/recall/F1 are the maximum over thresholds of a noisy quantity, an optimistically biased estimate. The threshold also could not have been known at deployment time.

Caught by: `test_threshold_never_sees_test_rows`, `test_test_metrics_are_computed_at_the_frozen_threshold`.
