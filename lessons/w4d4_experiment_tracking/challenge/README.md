# Challenge — compare two groups of runs, paired on the seed

Independent work. Aim for 45 minutes. The reference solution is not in this folder.

The registry now holds, for example, isolation forests with 50 and with 200 trees, three seeds each.
"200 trees is better by 0.013" compares two means; each mean is affected by which seeds were run. When
group A and group B were run with the *same* seeds and the seed controls shared randomness (here the
same forests are not shared, but in many tasks the seed fixes the data subsample or the split), the
honest comparison is over **paired** differences: (A, seed s) minus (B, seed s).

## Task

Implement `challenge/compare_groups.py`:

1. `compare_groups(index, a, b, metric, pair_on="seed") -> dict`
   * `index` is a DataFrame as built by `build_index` (columns `run_id`, `status`, `seed`, `sweep`,
     `param.*`, `metric.*`).
   * `a` and `b` are filters `{dotted parameter key: value}`, matched against `param.<key>` columns (a key
     that is itself a column, such as `sweep`, is matched directly). Unknown keys raise `ValueError`.
   * Only **complete** runs count.
   * Pair runs on `pair_on`; values present in only one group are left out and listed in
     `unmatched_a` / `unmatched_b`.
   * If a filter leaves more than one run for the same `pair_on` value (the filter does not identify
     one configuration), raise `ValueError`. If no value is shared, raise `ValueError`.
   * Return `metric`, `n_pairs`, `pairs` (a list of `{pair_on: value, "a": ..., "b": ..., "diff": a - b}`
     sorted by the pairing value), `mean_diff` (mean of the paired differences), `sd_diff` (ddof 1; NaN
     for a single pair), `a_better` (number of positive differences), `unmatched_a`, `unmatched_b`.
2. `format_report(result, a, b) -> str`: a readable report with one table row per pair, the mean and sd
   of the differences, and the unpaired values.
3. (Not checked) a small command line: `python challenge/compare_groups.py --runs-dir runs
   --a detector.n_estimators=200 --b detector.n_estimators=50 --metric dev_pooled_pr_auc`.

```bash
python wb.py check w4d4 --challenge
```

## Acceptance criteria

* All challenge checks pass.
* You ran it on your SKAB registry and can state, in one sentence, what the paired result does and does
  not show about 200 versus 50 trees (consider how many pairs there are, and what the seed controls in
  an isolation forest).
