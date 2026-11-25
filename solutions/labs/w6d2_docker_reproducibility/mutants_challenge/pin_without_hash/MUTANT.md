# pin_without_hash
Plausible mistake: an exact pin without a hash. The version is right, but in hash-checking mode (which build.sh now uses) pip refuses it, and without that mode nothing guarantees which file is installed. Expected to fail: test_lock_hash_is_the_hash_of_that_wheel and the install check.
