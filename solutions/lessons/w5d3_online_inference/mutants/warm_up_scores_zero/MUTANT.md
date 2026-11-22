# Mutant: warm_up_scores_zero

Returns score 0.0 during warm-up instead of None. A fabricated number looks like "perfectly normal"
to every consumer (dashboards, alert rules, averages) although nothing was measured.
