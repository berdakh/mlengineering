# Mutant: one-sided test reported as two-sided

The statistic is the signed mean, so only improvements in the expected direction count as extreme.
Power looks better (the rejection region is twice as large on the side that matters) and the
"required number of experiments" comes out smaller.

Why it is tempting: "we only care whether the new model is better". But a one-sided test at 0.05 is a
two-sided test at 0.10; when the direction was chosen after seeing the data, the false-positive rate
doubles. Rejected by `test_power_matches_known_answer` (power too high at moderate effects).
