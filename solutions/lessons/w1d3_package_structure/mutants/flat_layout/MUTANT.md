# Mutant: flat layout

The package directory sits next to `pyproject.toml` instead of under `src/`.
Everything "works" when run from the project root, because the current directory
is first on `sys.path` - installed or not. That is exactly why it is rejected:
the learner cannot tell whether they are testing the installed package or the
working tree, and a broken `pyproject.toml` goes unnoticed.

Rejected by: `test_src_layout` (via the `src` fixture).
