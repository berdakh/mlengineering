# smoke_no_wait
Plausible mistake: asking /readyz once and failing if it is not 200. Against a container that was just started this is flaky: it fails whenever the model takes a moment to load. Expected to fail: test_waits_for_a_service_that_is_still_starting.
