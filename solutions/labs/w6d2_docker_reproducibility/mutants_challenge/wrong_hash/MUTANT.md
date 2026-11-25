# wrong_hash
Plausible mistake: the right version with a hash copied from the wrong wheel (here the 1.1.0 file). pip detects the mismatch and refuses to install: hash checking doing its job. Expected to fail: test_lock_hash_is_the_hash_of_that_wheel and the install check.
