# Mutant: a bundle without provenance

`build-model` writes a valid, loadable bundle that does not say which config and which split manifest
it came from. Everything runs; nobody can later tell whether the deployed model matches the report.
