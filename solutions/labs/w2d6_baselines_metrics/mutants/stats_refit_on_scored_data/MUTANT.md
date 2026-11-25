# stats_refit_on_scored_data

`score()` standardises with the mean and standard deviation of the frame being scored instead of the statistics learned in `fit()`.

Why it is plausible: it is `StandardScaler().fit_transform(X_test)`, the habit of z-scoring whatever array is in hand; in signal-processing work per-recording normalisation is common and often legitimate.

Why it is wrong here: the scored frame contains the anomalies, so their own shift moves the mean and inflates the variance (test-set statistics leak into the score), and a row's score changes with the batch it arrives in, which makes online scoring impossible. Per-experiment calibration is legitimate only on rows known to precede evaluation (`burn_in_scores`).

Caught by: `test_a_row_score_does_not_depend_on_the_other_rows_scored`.
