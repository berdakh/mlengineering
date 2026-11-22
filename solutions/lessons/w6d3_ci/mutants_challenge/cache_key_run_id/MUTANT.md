# Mutant: hashFiles added, but the key still ends in a per-run value
github.run_id is unique per workflow run, so the key still never repeats.
Caught by: test_cache_key_is_stable_and_tracks_dependencies.
