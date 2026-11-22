# Mutant: closed loop
Each request waits for the previous response. Under a slow server the generator sends fewer requests
than scheduled and the server never sees the intended load. Caught by: test_open_loop_keeps_the_schedule_when_responses_are_slow.
