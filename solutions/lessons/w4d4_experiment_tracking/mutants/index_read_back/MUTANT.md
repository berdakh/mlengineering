# Mutant: the index file is treated as the source of truth

Once index.csv exists it is read back instead of rebuilt, so deleted, added or repaired run
directories are invisible to the table. Caught by: the rebuild-from-disk check.
