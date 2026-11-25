# Mutant: the new subcommand bypasses the error handling

`train` was already wrapped in `try/except`; the new `features` branch was added
above it. A missing input to `features` now ends in a traceback and exit code 1,
while `train` still behaves. Typical of bolting a second command onto a `main()`
that was written for one.

Rejected by: `test_missing_inputs_are_clean_errors[features ...]`.
