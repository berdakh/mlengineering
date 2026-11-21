# score_is_normality

`MahalanobisScorer.score` returns a Gaussian likelihood: high for normal rows, low for anomalous ones.

Why it is plausible: density models naturally produce 'probability of the data'; scikit-learn's `score_samples` and `decision_function` for outlier detectors also follow higher = more normal, the opposite of this project's convention.

Why it is wrong: every downstream consumer (threshold `>=`, PR-AUC, the API) assumes higher = more anomalous. A flipped sign yields a PR-AUC below prevalence, which a constant-score floor in the table makes visible.

Caught by: `test_higher_score_means_more_anomalous`, `test_mahalanobis_catches_a_broken_correlation`.
