# Mutant: global_time_index

Kept from the notebook: sort the whole table by `datetime` and use the global row number as `t`.
`t` is then not a within-experiment index (a rolling window or a `diff` silently spans two
experiments), and because several real SKAB files overlap in wall-clock time, rows of different
experiments are interleaved.

Rejected by `test_t_is_a_per_experiment_time_index`.
