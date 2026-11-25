# Mutant: entry point names a callable that does not exist

`[project.scripts] pumpwatch = "pumpwatch.cli:run"` but the function is `main`.
`pip install -e .` still succeeds - entry points are not validated at install
time - and the failure only appears when someone types `pumpwatch`
(`ImportError: cannot import name 'run'`). `python -m pumpwatch.cli` keeps
working, which is why this slips through when only that form is tried.

Rejected by: `test_entry_point_resolves_to_a_callable` and the CLI checks.
