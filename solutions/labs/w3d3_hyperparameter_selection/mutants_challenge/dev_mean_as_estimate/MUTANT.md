# Mutant: the chosen trial's own dev mean is reported as the estimate

The choice is sensible (one-SE rule) but the number attached to it is the mean of the very fold
scores that got the trial chosen. Over 200 generated tables that number is too high by 0.0155 on
average. It is the most natural thing to write in a results table, which is why it is here.

Rejected by: `test_estimate_is_unbiased_for_the_chosen_trial`.
