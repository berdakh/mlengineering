# Mutant: re-registering a version replaces it

`register` deletes an existing version and copies the new bundle in its place. Every prediction already
logged with `model_version = 1.0.0` now points at a different function. Caught by
`test_register_creates_an_immutable_version`.
