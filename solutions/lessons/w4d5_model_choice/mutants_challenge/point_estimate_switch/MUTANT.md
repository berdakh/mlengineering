# Mutant: switch whenever B's point estimate is ahead and fast enough

Chooses B when diff > 0 and B meets the budget, ignoring the interval and the MPID. With a 500 ms
budget the +0.011 point estimate wins. Caught by `test_small_gain_does_not_win_even_when_fast_enough`.
