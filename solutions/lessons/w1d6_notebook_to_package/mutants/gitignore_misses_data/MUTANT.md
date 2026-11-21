# Mutant: gitignore_misses_data

The `.gitignore` covers Python debris but not `data/`. The first `git add .` after running the
download script commits 4.3 MB of GPL-licensed third-party data into history, where deleting the
files later does not remove them.

Rejected by `test_gitignore_keeps_data_and_debris_out`.
