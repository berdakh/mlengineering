# w1d6 challenge: a sampling-gap report, test-first, on a branch

**Time:** about 40 minutes. **Assistance:** none beyond hint 1. **Where:** your `flowguard` repository.

## Situation

The notebook has a cell that prints `median dt 1.0 max dt 1887107.0 n gaps > 5 s: 19`. A maximum
interval of 21.8 days between "consecutive" samples of a 1 Hz recording is not a sampling gap.
The project needs the true list of gaps: causal rolling features (w2d5) and detection delays (w3d4)
are both wrong across a hole in the data, so the pipeline has to know where the holes are.

## Task

On a branch `gaps`, with tests written before or alongside the implementation:

1. `flowguard.data.find_gaps(tidy, max_gap_seconds=5.0) -> pandas.DataFrame`
   One row per gap, where a gap is a pair of **consecutive rows of the same experiment** whose
   timestamps differ by **strictly more** than `max_gap_seconds`. Columns (at least):
   `experiment_id`, `gap_start` (timestamp before the gap), `gap_end` (timestamp after it),
   `gap_seconds` (a number, in seconds). No gaps gives an empty frame that still has these columns.
   A negative threshold raises `ValueError`.
2. `flowguard gaps --raw-dir <dir> [--max-gap-seconds S]` prints one JSON document:
   `{"max_gap_seconds": S, "n_gaps": N, "gaps": [{"experiment_id", "gap_start", "gap_end", "gap_seconds"}, ...]}`.
   Errors behave like `summary`: one line on stderr, non-zero exit, nothing on stdout.
3. Add a row to `NOTES.md`: the notebook's count, yours, and the mechanism behind the difference.
4. Merge the branch into `main` when the tests pass. `summary` must keep working.

## Acceptance criteria

- [ ] `WB_TARGET_DIR=<your repo> python -m pytest labs/w1d6_notebook_to_package/checks_challenge -q` passes.
- [ ] Your own tests include: a gap inside one experiment; two experiments far apart in time with no gap in either; an interval exactly equal to the threshold.
- [ ] `git log --oneline main..gaps` (before merging) showed at least three commits, and the first one that touches `find_gaps` adds a failing or newly passing test, not just code.
- [ ] On the real data you can state how many gaps longer than 5 s exist, in how many experiments, and the longest one. Write the three numbers in `NOTES.md`.
- [ ] You can explain in two sentences why the notebook's count was wrong *twice over*.

## Optional extension question (no code required)

The notebook's summary table shows one experiment ending at `18:11:02` and the next one starting at
`18:10:42` on the same day. Recordings from one testbed cannot overlap. Investigate with your
package: what is going on, how many rows are involved, and why will it matter when experiments are
assigned to training and test sets? The reference notes give the answer with numbers.

No solution is given here. Hints are in `../hints/`; the reference is in
`solutions/labs/w1d6_notebook_to_package/challenge/`.
