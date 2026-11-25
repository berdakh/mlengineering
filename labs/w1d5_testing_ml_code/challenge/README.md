# w1d5 independent challenge — test and repair `detect_events`

**Kind:** independent demonstration (transfer). **Time:** about 40 minutes.
**No solution here.** Reference: `solutions/labs/w1d5_testing_ml_code/challenge/` — open it only after your attempt.

## Context

A detector emits one anomaly score per sample. Operations do not page an engineer per
sample; they page per *event*. `eventkit.events.detect_events` performs that conversion.
It is the same post-processing used in many detectors, from seizure detection in EEG to alarm systems (threshold, join
fragments, enforce a minimum duration), and the portfolio project will use it for
event-level evaluation in Week 3.

The file `eventkit/events.py` was written quickly and never tested. It contains defects.
How many is not disclosed.

## Specification

```
detect_events(score, threshold, min_samples=1, merge_gap=0) -> list[tuple[int, int]]
```

1. `score` is a one-dimensional sequence of floats (list or NumPy array). It is not modified.
2. A sample is *above* when `score[i] > threshold` (strictly). A NaN score is never above.
3. A *run* is a maximal block of consecutive above samples.
4. Two neighbouring runs are **merged** into one event when the number of non-above samples
   between them is `<= merge_gap`. Merging chains: A–B–C can become one event.
   With `merge_gap=0` nothing is merged.
5. **After** merging, an event is kept only if its length `stop - start >= min_samples`.
6. Events are returned in increasing order as half-open index pairs `(start, stop)`:
   `start` is the first sample of the event, `stop` is one past its last sample.
   An event may begin at index 0 and may end at `len(score)`.
7. Empty input returns `[]`.
8. `ValueError` is raised if `score` is not one-dimensional, if `min_samples < 1`, or if `merge_gap < 0`.

## Your task

1. Write tests in `tests/test_events.py` **from the specification above**, not from what the
   code currently does.
2. Use them to find the defects; repair `eventkit/events.py`. Keep the signature.
3. Add to the top of your test file a comment block (5–10 lines): the defects you found,
   and for each one the test that exposed it.

Run your tests:

```bash
cd labs/w1d5_testing_ml_code/challenge
python -m pytest -q
```

## Acceptance criteria

Automated (`python -m pytest labs/w1d5_testing_ml_code/checks_challenge -q` from the repo root):

- [ ] Your repaired `detect_events` agrees with the specification on 400 random score
      arrays (with ties at the threshold and NaNs) and on the error contracts.
- [ ] Your tests pass against a correct implementation — i.e. they assert nothing the spec does not promise.
- [ ] Your tests fail against each of 8 defective implementations (the defects you were
      given are among them; the others are mistakes of the same kind).
- [ ] Your tests run in under 10 seconds, from any directory, without network access.

Not automated — judge yourself against the rubric in `../assessment.md`:

- [ ] Each test name states the clause of the spec it checks.
- [ ] The defect log (task 3) is accurate.
- [ ] You did not open `checks_challenge/` (it contains implementations) or hints 3–4 before
      passing. If you did, mark the challenge as guided practice rather than independent skill.

## What you may use

The lesson, handbook H9.1, pytest and NumPy documentation, hints 1–2.
