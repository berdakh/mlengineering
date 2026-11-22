# Mutant: the test is marked perf but the default run still includes it
The marker is registered and the scheduled workflow exists, but nothing deselects perf tests from the push run.
Caught by: test_default_run_has_no_wall_clock_assertion.
