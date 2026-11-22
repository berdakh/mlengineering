# Hint 2 - build masks, then test them with properties

**Lab.**

1. `required_purge`: spans intersect iff $|i-j| \le w - 1 + h$, so drop that many rows on each side.
2. `group_kfold_indices`: shuffle the *unique groups* with the seed, deal them into folds, then map back
   to rows. Assert in a REPL that the group sets of train and validation are disjoint.
3. `grouped_folds`: read the folds from the manifest; before returning, raise if any test or reference
   experiment appears in a fold, or if an overlap group's members are spread over folds.
4. `leave_one_family_out`: for each family, validation = its experiments; training = the other
   labelled experiments *minus* any that share an overlap group with a validation experiment.
5. `purged_time_split`: `np.array_split(np.arange(n), n_splits)` gives the blocks; training is
   everything outside `[start - purge, end + embargo]`.
6. `forward_chaining_split`: `n_splits + 1` blocks; fold k validates block k+1 and trains on
   `0 .. start - gap - 1`.

Write one property test per function before running the checks: blocks cover `range(n)` exactly once;
no training index within the buffer; group sets disjoint.

**Challenge.** Three boolean masks per cut-off *c*, on rows with a label:
`train = week + label_weeks <= c`; validation = `c < week <= c + horizon_weeks`; split validation by
whether the store appears in `train`. Then check the planted-shock property yourself: if training
labels end at week *c* rather than *c - 4*, the last training labels share weeks with the first
validation labels.
