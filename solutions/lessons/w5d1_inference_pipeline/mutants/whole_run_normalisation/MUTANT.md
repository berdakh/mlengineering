# Mutant: the whole run calibrates itself

`score_batch` calibrates each run on ALL of its rows instead of its first `n_burn` rows ("normalise the
input"). The fault itself then enters the mean and standard deviation and is partly normalised away,
and a fault late in a run changes the scores of rows before it. Caught by
`test_a_later_fault_does_not_change_earlier_scores`, `test_planted_shift_is_not_normalised_away` and
the parity test.
