# Mutant: basicconfig_at_import

A library module calls `logging.basicConfig` at import time. Importing `pumpwatch.features` from a notebook, a test, or a web service now reconfigures the host application's root logger. Caught by `test_importing_the_library_does_not_configure_logging`.

Changed file: `src/pumpwatch/features.py`
