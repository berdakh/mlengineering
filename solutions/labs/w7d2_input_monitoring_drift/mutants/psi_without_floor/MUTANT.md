# Mutant: PSI without the epsilon floor

Empty bins give log(0); `nansum` then silently drops exactly the bins where all the drift is. Caught by `test_psi_with_an_empty_bin_is_finite_and_uses_eps`.
