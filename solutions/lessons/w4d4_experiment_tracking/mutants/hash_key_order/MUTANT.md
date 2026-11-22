# Mutant: the hash depends on key order

`json.dumps` without `sort_keys=True` serialises dicts in insertion order, so the same configuration
built in a different order gets a different run id, and a completed run is repeated under a new
name. Caught by: the identity check.
