# Mutant: seed_not_threaded

The seed is loaded, validated, logged and saved in the snapshot, but never passed to the split, which falls back to its default argument. Every run 'with a different seed' evaluates the same held-out units. Caught by `test_seed_from_config_controls_the_split`.

Changed file: `src/pumpwatch/cli.py`
