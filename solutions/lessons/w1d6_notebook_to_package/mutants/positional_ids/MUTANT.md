# Mutant: positional_ids

The notebook's `enumerate` habit survived the refactor: the experiment id is the file's position in
a sorted listing, not its name. Lexicographic order is `0, 1, 10, 2`, so `valve1/10.csv` becomes
`valve1/2` and every later analysis, split manifest and error report refers to the wrong recording.
On the real data this mislabels 28 of the 34 labelled experiments (`other/` files are numbered from 1,
so all 14 of them shift).

Rejected by `test_experiment_ids_come_from_file_names` and `test_summary_command`. The mutant's own
tests are weakened the way a learner's would be (they never use a two-digit file name).
