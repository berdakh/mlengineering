# Mutant: scikit-learn is imported but not declared

The author's environment already had scikit-learn, so nothing failed locally.
In a clean environment `pip install .` succeeds and `pumpwatch train` dies with
`ModuleNotFoundError: No module named 'sklearn'`.

Rejected by: `test_runtime_dependencies_declared`.
