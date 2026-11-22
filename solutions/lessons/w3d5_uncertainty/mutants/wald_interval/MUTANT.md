# Mutant: Wald (normal-approximation) interval under the name `wilson_interval`

`p +/- z * sqrt(p (1 - p) / n)`, the formula from an introductory course. With 9 of 9 events
detected it returns the zero-width interval [1, 1]; with 1 of 9 the lower bound is negative.

Why it is tempting: it is the formula most people remember, and it is fine for p near 0.5 with large n,
which is exactly the case that small event counts are not.

Rejected by: `test_wilson_matches_reference`, `test_wilson_seven_of_nine_is_wide`.
