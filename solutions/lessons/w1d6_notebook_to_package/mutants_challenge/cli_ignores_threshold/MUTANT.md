# Mutant: cli_ignores_threshold

The option `--max-gap-seconds` is parsed and then never used: the command always reports gaps longer
than 5 s. The function is correct and unit-tested; the wiring is not tested at all. A classic gap
between "the function works" and "the command does what its help text says".

Rejected by `test_gaps_command_uses_the_threshold_argument` and `test_gaps_command_rejects_bad_input_cleanly`.
