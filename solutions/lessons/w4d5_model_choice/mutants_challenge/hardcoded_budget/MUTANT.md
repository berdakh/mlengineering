# Mutant: decision parameters hard-coded

Uses 50 ms and 0.02 written in the code instead of the values in case.json, so the same code gives the
wrong answer the day the product team changes the budget. Caught by
`test_small_gain_does_not_win_even_when_fast_enough` (500 ms budget) and `test_latency_budget_is_a_hard_constraint` (5 ms).
