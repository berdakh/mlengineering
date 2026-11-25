# Mutant: no `__main__.py`

The console script works, so the author never noticed that `python -m pumpwatch`
fails with "No module named pumpwatch.__main__; 'pumpwatch' is a package and
cannot be directly executed". `python -m pumpwatch.cli` works and is easily
mistaken for the same thing.

Rejected by: `test_python_dash_m_matches_console_script`.
