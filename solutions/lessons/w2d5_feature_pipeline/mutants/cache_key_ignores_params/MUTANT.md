# Mutant: cache_key_ignores_params

The cache key is built from the data hash only. Asking for different windows returns the previously cached table for the old windows, silently. The metadata even records the new parameters on a first write, so the directory looks right. Typical cause: adding a parameter later and forgetting it is part of the identity of the output. Caught by the changed-parameter cache checks.

Changed file: `src/flowguard/cli.py`
