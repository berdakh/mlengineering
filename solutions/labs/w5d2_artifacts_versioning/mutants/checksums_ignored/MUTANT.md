# Mutant: checksums written but never checked on load

`save_bundle` writes `checksums.json`, `verify_bundle` exists and `register` calls it, but `load_bundle`
skips it ("the registry already verified it"). A file edited after registration, by a person or a
faulty sync, loads as if nothing happened. Caught by `test_tampered_file_is_refused_and_named`,
`test_missing_file_is_refused` and `test_unlisted_file_is_refused`.
