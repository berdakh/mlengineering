# Isolation-forest score not negated

Returns sklearn's score_samples directly. In sklearn that score is HIGHER for normal points, so the
detector ranks outliers last.
