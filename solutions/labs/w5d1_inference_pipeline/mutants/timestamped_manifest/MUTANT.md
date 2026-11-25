# Mutant: a timestamp in the manifest

`manifest.json` records `created_at` (the wall-clock time). Natural, and it makes the command not
idempotent: re-running on the same input and model changes the bytes of the output, so a downstream
job cannot tell "nothing changed" from "recomputed". Caught by `test_rerun_is_byte_identical`.
