# Mutant: unknown_keys_accepted

Unknown keys are dropped instead of rejected, so a typo such as `split.sed = 3` or `--set model.depth=3` runs with the default and nobody notices. This is the default behaviour of the common `cfg.get('seed', 7)` idiom. Caught by the validation checks.

Changed file: `src/pumpwatch/config.py`
