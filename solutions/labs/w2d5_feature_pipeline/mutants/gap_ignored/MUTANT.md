# Mutant: gap_ignored

Experiments are grouped correctly but time gaps inside an experiment are ignored: a 30-row window is treated as 30 seconds even when it bridges a multi-minute hole in the recording. Slopes and differences across the hole are meaningless. Typical cause: thinking in row counts and never looking at `datetime.diff()`. Caught by the gap-reset test and the slow-reference comparison.

Changed file: `src/flowguard/features.py`
