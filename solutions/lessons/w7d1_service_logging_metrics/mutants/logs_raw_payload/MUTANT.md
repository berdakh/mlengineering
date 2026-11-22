# Mutant: logs the full request payload

The prediction event carries every sample "for debugging". Raw payloads in logs leak data, cost storage, and make logs unreadable. Caught by `test_raw_sample_values_are_never_logged`.
