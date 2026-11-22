# Mutant: population standard deviation

`np.std` defaults to ddof = 0, which underestimates the spread of a handful of seeds
(by a factor sqrt((n-1)/n): 11% at n = 5). Caught by: the summary check.
