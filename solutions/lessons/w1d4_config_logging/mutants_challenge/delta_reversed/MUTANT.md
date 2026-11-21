# Mutant: delta_reversed

`delta` is computed as a - b instead of b - a. The report looks plausible; the sign of every improvement is wrong. Caught by the delta checks.

Changed file: `src/pumpwatch/compare.py`
