# w1d5 — assessment answers, common incorrect answers, retrieval key

Model answers are deliberately short. Wording will differ; score against the rubric in
`lessons/w1d5_testing_ml_code/assessment.md`.

## Part A

**A1. `expected = np.sqrt(np.mean(x**2))` vs `rms(x)`.**
It is a *differential* test against a one-line re-derivation. It is useful: it kills
"missing sqrt" and "mean-abs" because the test's formula is written independently from the
definition. Its weakness is that the oracle is the same formula a developer would type into
the implementation, so a shared misunderstanding (e.g. both forget to handle NaN, both use
the wrong axis for 2-D input) passes. It also says nothing an auditor can check by eye.
A sine with a closed-form answer is independent of *any* code.
- *Common incorrect answer:* "It is a tautology, therefore useless." Not so — it is
  tautological only if `expected` is produced by calling the code under test. Re-deriving
  from the definition is a weaker oracle, not a non-oracle.
- *Common incorrect answer:* "It is fine because random inputs cover more cases." Coverage of
  inputs is not the issue; independence of the expected value is.

**A2. Layers.**
(a) Unit test (structural contract of the split) — blocks a merge.
(b) Data validation — it is a statement about *today's file*, runs in the pipeline at load
time, and should stop that pipeline run (not a code merge; the code did not change).
(c) Statistical performance check — belongs to model evaluation/promotion, reported with
uncertainty; it should gate *promoting a model*, not merging code, because it can fail by
chance and pass with defects.
(d) Integration/smoke test — deterministic by construction, blocks a merge.
- *Common incorrect answer:* putting (c) in the unit suite "because model quality is what
  matters". It matters, and that is why it deserves an instrument with known variance; see
  the 0.946–1.000 spread from `example/metric_variability.py`.
- *Common incorrect answer:* calling (b) a unit test. Unit tests run on fixed inputs chosen
  by the author; data validation runs on inputs chosen by the world.

**A3. 0.4911 instead of 0.5.**
Cause: with `N=128`, `fs=256` the bins are 2 Hz apart; 25 Hz lies between bins (12.5
periods in the window), so the tone's energy leaks into neighbouring bins, some of them
outside 10–40 Hz, and the window no longer holds whole periods of the mean-removed signal
(its variance is 0.4993, not 0.5). The function is right; the test input does not have the
property the oracle assumes.
Good repair: use a frequency on a bin (24 or 26 Hz) so the closed-form answer is exact, keep `rel=1e-9`.
Bad repair: widen to `rel=0.05`. That admits real defects of up to 5 % and hides the reason.
(A legitimate third option: keep 25 Hz and assert a *bound* you can justify, labelled as such.)
- *Common incorrect answer:* "Floating-point error." Rounding error here is ~1e-14; a 1.8 %
  discrepancy is physics of the DFT, not arithmetic.
- *Common incorrect answer:* "`band_power` should apply a window function." Possibly a
  reasonable feature request, but it changes the function's contract; it is not a reason for
  the test to fail.

**A4. 100 % coverage ≠ correct.**
The `runs_without_error` suite (in `mutants/`) executes every feature function and all 14
injected defects survive it; e.g. `rms` without the square root still returns a positive
float. Coverage counts executed lines, not verified results.
- *Common incorrect answer:* "Coverage is useless." Low coverage is strong evidence of
  missing tests; high coverage is weak evidence of anything.

**A5. "Same seed → same split" passes; what can still be wrong?**
(1) The `seed` argument is ignored (hard-coded `random_state`): the split is perfectly
reproducible. Detect by varying the seed and requiring more than one distinct test set.
(2) The split leaks units (row-level shuffle with a fixed seed is also reproducible).
Detect with the disjointness assertion on group ids. (Also acceptable: wrong test fraction.)
- *Common incorrect answer:* "Non-determinism." That is the one thing this test *does* detect.

**A6. Why the scaler leak resists unit testing.**
From outside, `train_and_evaluate` returns metrics; whether the scaler's statistics included
test rows changes them only slightly (in w1d3 the printed metrics were identical). There is
no observable contract to assert without reaching into internals. The effective control is
*design*: put preprocessing inside the estimator (`Pipeline`) so the leak cannot be
expressed, and review experimental design. (A test is possible — e.g. make test rows
extreme outliers and assert that training-set scaling statistics are unaffected — but it is
contrived and couples the test to internals.) Lesson: tests are one control among several
(types, API design that makes misuse impossible, review, evaluation protocol); choose the
cheapest control that actually closes the failure mode.
- *Common incorrect answer:* "Assert the metric did not change." Circular, and the metric
  did not change in the first place.

## Part B

**B1. Why unit tests must not read the repository's data file.**
Level-3 answer contains these points:
1. *Diagnosis.* A unit test's value is that a failure localises a code defect. If the test
   reads a shared file, a failure can also mean the file changed, moved, or is absent — the
   test now detects three things and identifies none.
2. *Oracle.* On real data nobody knows the right RMS of window 17. The only possible
   assertion is "same as last time", a characterisation test, which pins bugs as firmly as
   correct behaviour.
3. *Portability and speed.* Tests must run from any directory, in CI, in a container, and
   in seconds; a 1 MB CSV today is a 20 GB table next quarter.
4. *What to do for realism.* Keep a tiny, hand-checkable fixture (a few rows written by the
   test into `tmp_path`); add a separately marked integration test that runs the pipeline on
   a small committed sample; and move "is today's real data sane?" into data-validation
   checks that run in the pipeline (Week 2).
5. *Boundary of the rule.* A committed golden file is appropriate for *regression* tests of
   a parser or a serialisation format, where "byte-identical to last release" is the contract.
- *Common incorrect answer:* "Because it is slow." True, but the weakest reason; it suggests
  a fast real file would be fine.
- *Common incorrect answer:* "Real data should never be used in tests." Too strong — see
  points 4 and 5.

## Part C — interview rep

Reference: `interview_rep/merge_intervals.py` and `test_merge_intervals.py` (12 tests, executed).
Boundary cases a strong answer lists *before* coding: empty list; single interval; touching
(merged, by the prompt); gap of one (not merged); containment (`(1,10),(2,3)` — the bug is
taking the later `stop` instead of the max); unsorted input; duplicates; whether the input
may be mutated. Complexity: O(n log n) from the sort, O(n) merge pass.
Most frequent defects: `merged[-1] = (merged[-1][0], stop)` without `max`; `<` instead of
`<=` for touching; sorting the caller's list in place.

## Retrieval-practice key (lesson §8)

The two problems: (1) the oracle is the code's own earlier output, so the test can only
detect *change*, not error — if the notebook run had the factor-of-two bug, the test
enforces it; (2) `rel=0.2` is not derived from anything: it is far above numerical noise and
its relation to the defects of interest is unknown (a factor of two happens to exceed it,
a 15 % normalisation error does not).
Redesign: input = pure tone at a bin frequency inside 8–12 Hz with amplitude `A` (choose
`fs`, `N` so that e.g. 10 Hz is a bin); expected power `A²/2` from theory; tolerance
`rel≈1e-9`; add Parseval on noise for the normalisation, and a tone at exactly 12 Hz to pin
the half-open edge.

## Notes on the lab and challenge solutions

- Lab reference: `lab/tests/` (39 tests, ≈ 2 s). See `lab/README.md` for what to compare.
- Challenge reference: `challenge/eventkit/events.py` and `challenge/tests/test_events.py`.
  The three planted defects in the shipped file: (1) an event still open at the end of the
  array is dropped; (2) `>=` instead of `>` (which also changes nothing for NaN but admits
  ties); (3) short runs are filtered *before* merging, so a fragmented event disappears.
- Weak-suite mutants with measured survivors: `mutants/*/MUTANT.md`, `mutants_challenge/*/MUTANT.md`.
