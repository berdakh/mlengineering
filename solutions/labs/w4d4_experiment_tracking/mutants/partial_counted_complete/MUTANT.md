# Mutant: a run is complete when metrics.json exists

A run that crashed after writing metrics but before finishing (status.json missing) is counted as
complete and averaged in. Completion must be signalled by the LAST file written. Caught by: the
partial-run checks.
