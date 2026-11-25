# Mutant: one bad run fails the whole batch

`score_batch` raises `ValueError` as soon as one run cannot be scored, so one short or gappy run stops
every other run's predictions (and the CLI exits 1). Caught by `test_unscorable_runs_fail_alone` and
`test_partial_failure_scores_the_rest_and_exits_3`.
