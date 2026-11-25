# diagonal_covariance

`MahalanobisScorer` uses only the per-sensor variances (identity correlation matrix), so it computes the Euclidean norm of the z-vector.

Why it is plausible: it is numerically safe, never singular, and on SKAB it scores about as well as the full version, so the table gives no hint that anything is missing.

Why it is wrong: it is not the Mahalanobis distance. It cannot see an anomaly that breaks a relationship between sensors while each sensor stays in range, which is the only reason to prefer this scorer over max |z|.

Caught by: `test_mahalanobis_catches_a_broken_correlation`.
