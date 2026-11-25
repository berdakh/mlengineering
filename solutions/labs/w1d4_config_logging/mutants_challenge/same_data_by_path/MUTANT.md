# Mutant: same_data_by_path

`same_data` compares file paths instead of content hashes: a file edited in place is reported as the same data, and an identical copy as different data. Caught by the two `same_data` checks.

Changed file: `src/pumpwatch/compare.py`
