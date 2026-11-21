# w1d6 assessment: model answers

Open after writing your own. Numbers are from runs on the real data in the authoring session
(2026-11-21); details in `lab/NOTES.md`.

## A. Reasoning questions

### Q1. Order dependence

Run top to bottom, `df` was last assigned in the cell "look at one experiment":
`df = all_df[all_df.experiment_id == "other/2"]`. So the "normal" mean and standard deviation come
from one labelled experiment, 1,190 rows, **including its anomalous segment**, and because of the
positional-id bug that experiment is really `other/11.csv`. The comment says "against normal"; no
fault-free data is involved, and in fact none is left in `all_df` (it was dropped by `dropna()`).

Third outcome: in the live kernel, if the author ran this cell before the "look at one experiment"
cell, `df` was whatever the last loading loop left behind, i.e. the last file of the `other/` loop
(`9.csv`, raw and unsorted into the table), and the printed medians were different again. The
exported file cannot tell you which of these the author saw.

*Common incorrect answers*

- "`df` is the whole table." No: `all_df` is the whole table; `df` is assigned in four different cells as a scratch name.
- "It uses the anomaly-free data because that was loaded last." That frame is called `free`, never `df`.
- Stopping at "it is the wrong experiment" without noticing it contains anomalies, which is what makes it conceptually wrong rather than just mislabelled.

### Q2. What the cleaning step removed

The 9,405 rows are the entire fault-free recording. Its file has nine columns (no `anomaly`,
`changepoint`), so after `pd.concat` those two columns are NaN for all of its rows, and `dropna()`
removes any row containing a NaN. Nothing else in the dataset has missing values, so *only* that
recording goes.

Why 37,401 is dangerous: it is exactly the number of labelled rows, a figure that appears in the
project brief. A wrong number that matches a known-correct number
for a different quantity passes every sanity check by eye. The loss is also total for one group, not
a thinning of all groups, so no per-experiment statistic looks odd. The only reference data for
semi-supervised detectors disappears with no error.

*Common incorrect answers*

- "Rows with sensor dropouts." There are none (no NaN in any sensor column); the question said "without running anything else", and the two shapes plus the nine-column file are sufficient.
- "Duplicates were removed." `dropna` does not deduplicate. (Duplicated rows do exist across files, 1,290 of them, and they are still there.)

### Q3. Design choice: unlabelled file

A defensible answer picks one option, argues against two others, and names a cost.

**(a) Fill with 0** (the reference choice). For: the upstream description states the recording is
fault-free, so 0 is a label, not an imputation; the tidy table keeps integer label columns and one
schema for every experiment; semi-supervised training ("fit on normal") can select `anomaly == 0`
without special cases. Against (b): nullable labels propagate NaN into every mean, metric and
`groupby`, and invite exactly the `dropna()` that caused the original bug. Against (c): raising makes
the most important reference recording unloadable and pushes a special case into every caller.
Cost of (a): the table no longer distinguishes "labelled normal by an annotator" from "normal by
construction of the experiment"; if that file ever contained an unrecorded disturbance, the label
would be confidently wrong. Makes easier: fitting reference statistics (w2d5), semi-supervised
baselines (w2d6). Makes riskier: event-level evaluation (w3d4), if someone includes this recording
in the denominator of false alarms per hour without noticing it has no events by design.

**(d) `is_labelled` column** is also defensible, usually combined with (a): explicit provenance at
the cost of one more column every consumer must remember. **(b)** is defensible only with a strict
rule that metrics are computed on `is_labelled` rows and with nullable integer dtype; say so.
**(c)** is defensible only if the loader takes an explicit `labelled=False` argument for that file.

*Common incorrect answers*

- "Fill with 0 because it is simplest" (no argument about meaning; Partial at most).
- "NaN is more honest" without saying how every downstream mean and metric will treat NaN.
- Any answer that does not record the decision somewhere (docstring, `NOTES.md`): an undocumented labelling decision is a defect regardless of which option was chosen.

### Q4. Commit boundaries

1. *Extract `load_raw` exactly as the notebook does it* (ids from `enumerate`), with the notebook's
   output unchanged. Evidence: unchanged characterization output or an unchanged per-experiment table.
2. *Add a failing test*: a constructed folder with `0.csv`, `2.csv`, `10.csv` of different lengths,
   asserting row counts per id. It can be committed marked as expected-to-fail, or together with 3.
3. *Fix: ids from file names (BEHAVIOUR CHANGE)*, with the test passing and `NOTES.md` recording
   that 28 of 34 ids change. Evidence: the test, and the changed table.

If the fix rides inside the extraction commit, the extraction can no longer be shown to be
behaviour-preserving (the output moved), and the id change cannot be attributed: a reviewer sees
40 lines of moved code and a different table, and has to re-derive which line did it. If you wrote
the package as new code rather than by editing the notebook, the equivalent discipline is: the
commit adding `load_raw` carries the hostile test, and `NOTES.md` attributes the disagreement with
the recorded notebook output.

*Common incorrect answers*

- "Fix it immediately, it is obviously a bug." Obvious bugs are the ones whose effects are least examined; here the fix renames most experiments, which every later artefact (split manifest, error report) depends on.
- "One commit with a good message is enough." The message can attribute; it cannot make the structural part verifiable.

### Q5. Limits of characterization tests

Any two of:

- **Output is known to be wrong in ways that make it not worth preserving** (today's notebook: most tables depend on the id bug). Use: hand-checkable unit tests on constructed inputs, and a discrepancy table against the old output.
- **Non-deterministic output** (unseeded randomness, timestamps, thread ordering, GPU nondeterminism). Use: fix seeds and inject the clock first (w1d4); or assert invariants and tolerances instead of exact text.
- **Output too large or too coupled to formatting** (plots, long tables). Use: pin intermediate *data* (a small frame, summary statistics with tolerances) rather than rendered output.
- **Inputs you ran do not exercise the code path** (a branch only taken for a file type you do not have). Characterization gives false confidence; construct the input.
- **Numerical code across library versions.** Exact-text goldens break on a last-digit change; use `pytest.approx` with a justified tolerance (w1d5).

*Common incorrect answer:* "when the code is simple". Simplicity is not the criterion; whether the current output is a meaningful reference is.

## B. Scoring your `NOTES.md`

Demonstrated: at least four discrepancies, each with both numbers, the mechanism (the specific line
or habit), and a statement of which value is right *with a reason independent of the new code* (for
example "46,806 equals the notebook's own first shape print" or "the file `other/2.csv` has 780
lines"). Partial: discrepancies listed with numbers but mechanisms missing or generic ("the notebook
had a bug"). Not yet: fewer than three, or the package's numbers asserted as right because they come
from the package.

## D. Interview rep (debugging)

### What a strong answer looks like

**Hypothesis ordering** (this is what is scored first). The symptom is *order dependence between
calls in one process*. So the first hypothesis is **shared mutable state that outlives a call**. Two
candidates are visible: the module-level `_CACHE` and the mutable default `overrides={}`.

1. *Is state shared across calls?* Experiment: call with an override, then without; compare.
   (`demo_order_dependence.py`: second default call returns `pressure: 1.5`.)
2. *Which object is being mutated?* Experiment: print `load_thresholds.__defaults__` and `_CACHE`
   after the calls. Result: the default is still `{}`; `_CACHE[path]` has changed.
3. *Is the returned object the cached object?* `load_thresholds(p) is load_thresholds(p)` is `True`.

**The defect.** `thresholds = _CACHE[path]` binds a second name to the cached dict; it does not copy.
`thresholds.update(overrides)` therefore writes the override into the cache permanently, and
returning that same dict lets any caller corrupt the cache by mutating the result. Two failure
routes, one cause: aliasing of a cached mutable object.

**The red herring.** `overrides={}` is the famous mutable-default pattern, and it is bad style, but
it is not the cause: the function never mutates `overrides`, only reads it. Evidence:
`load_thresholds.__defaults__` is still `({},)` after any sequence of calls. Naming it as the cause
without checking is the most common wrong answer. (It should still be changed to `None`: the next
edit that does mutate it would create a second bug.)

**Fix** (`thresholds_fixed.py`): cache the parsed file, return a new dict each time:
`return {**_CACHE[key], **(overrides or {})}`. Note for nested structures a shallow copy is not
enough; say so if the thresholds could be nested (`copy.deepcopy`, or cache an immutable form).

**Tests** (`test_thresholds.py`, four tests, run against both versions: 4 passed, 2 xfailed,
2 xpassed, i.e. the buggy version fails exactly the two below):

- an override in one call does not affect a later call without it;
- mutating the returned dict does not affect a later call.

Each test needs a fresh cache (`_CACHE.clear()` in a fixture); without that the *tests* are
order-dependent, which is the colleague's first symptom.

**Link to the lesson.** A module-level cache and a notebook kernel are the same thing: state that
persists between invocations and is invisible at the call site. `df` reused across cells and
`_CACHE[path]` aliased across calls fail for the same reason.

### Rubric

| Level | Description |
|---|---|
| **Demonstrated** | Starts from "shared mutable state", proposes cheap discriminating experiments before reading line by line, identifies aliasing of the cached dict, explicitly clears the mutable default with evidence, fixes with a copy while keeping the cache, gives both tests and mentions cache isolation between tests |
| **Partial** | Finds the cache mutation but only one failure route; or blames the default argument first and corrects after testing; fix removes the cache entirely (correct but changes the stated requirement) |
| **Not yet** | Blames the mutable default and stops; fix is `overrides=None` only (the bug remains: verify by running the tests); no test proposed |

### Common incorrect answers and why they fail

- **"The bug is the mutable default argument."** `overrides` is never mutated. Changing it to `None` leaves both tests failing.
- **"Tests fail together because of test ordering in pytest."** That names the symptom. Order matters *because* state leaks; pytest is behaving correctly.
- **"Remove the cache."** Fixes it but violates "parse each file once"; in a service this is a per-request disk read. Acceptable only if stated as a tradeoff.
- **`thresholds = _CACHE[path].copy()` and then caching the updated copy back.** Reintroduces the leak through a different door.
- **Deep-copy everything always.** Correct, and a cost worth mentioning; for a flat dict a shallow copy suffices.
