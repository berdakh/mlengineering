# pin_latest
Plausible mistake: compiling the lock today (uv pip compile / pip-compile) and committing it: it pins the newest release, 1.1.0, with a correct hash. Reproducible from now on, but it reproduces the wrong behaviour. Expected to fail: test_lock_pins_the_validated_version_exactly and test_installing_the_lock_reproduces_the_recorded_scores.
