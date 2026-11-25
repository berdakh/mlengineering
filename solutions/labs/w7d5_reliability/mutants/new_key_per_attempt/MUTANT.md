# Mutant: new_key_per_attempt

Each attempt gets a fresh `Idempotency-Key`, so the server cannot recognise a retry of a request it already processed (a duplicate side effect if the first attempt succeeded but its response was lost).
