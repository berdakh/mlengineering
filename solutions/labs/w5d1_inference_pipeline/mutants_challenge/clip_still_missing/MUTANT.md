# Mutant: two of three bugs fixed; the clip is still missing

Burn-in and feature order are fixed, so ordinary runs match exactly and a quick comparison on normal
data looks clean. Only runs that go far outside their start-up range (the faults) differ. Caught by
`test_serving_matches_training_beyond_the_clip`.
