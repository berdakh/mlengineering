# Mutant: the observed rate reported as the upper bound

`rate_upper_bound` returns `n / hours`.

**Why it is plausible.** It is the estimate everyone computes first, and with zero false alarms it
reads as a clean 0.00 per hour.

**What goes wrong.** Zero false alarms in 1.6 hours is compatible with a true rate of 1.8 per hour.
Reporting 0.00 as if it were a guarantee is the false claim this challenge exists to prevent.

**Caught by.** `test_rule_of_three`, `test_upper_bound_known_values_and_monotonicity`, `test_upper_bound_is_attached_and_is_not_the_point_estimate`.
