# range_with_hash
Plausible mistake: keeping a range (>=1.0,<1.1) and adding a hash. pip's hash-checking mode requires every requirement to be pinned with ==, so it refuses; and a range is not a lock. Expected to fail: test_lock_pins_the_validated_version_exactly and the install check.
