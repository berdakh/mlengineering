# b_user_only
Plausible mistake: fixing the security finding (USER app) and missing the signal problem: the CMD is still shell form, so /bin/sh is PID 1. Expected to fail: test_b_server_receives_sigterm.
