# Mutant: two version numbers

`pyproject.toml` was bumped to 0.6.0 by hand (static `version`), `flowguard.__version__` still says
0.5.0. The bundle and `/version` then report 0.5.0 for a 0.6.0 release.
