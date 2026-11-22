# Mutant: the detector is pickled "for convenience"

Next to the JSON, the bundle stores `detector.pkl` and `load_bundle` restores the detector from it.
It round-trips, it is checksummed, and loading it executes whatever the pickle stream says: a bundle
from an untrusted source is code. It also ties the artifact to the exact class layout of today's
code. Caught by `test_nothing_is_pickled` and `test_bundle_holds_exactly_the_documented_files`.
