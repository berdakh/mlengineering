# w2d7 - Week 2 review and catch-up (light day)

**Time budget: 60-90 minutes.** No new material.

| Activity | Time |
|---|---|
| 1. Spaced-review items due today (from `w1d7`) | 5-10 min |
| 2. Retrieval sheet, from memory | 25 min |
| 3. Score it; choose what to redo | 10 min |
| 4. Redo one thing, cold and unassisted | 20-30 min |
| 5. Interview set 2 (timed) | 45 min, or S1 + S2 only (20 min) on a short day |
| 6. Update progress flags and the spaced-review list | 5 min |

On a 60-minute day: activities 1-3, then either 4 or the short form of 5, then 6.

## Purpose

Week 2 moved from code structure to data: getting the right rows (SQL), trusting them (quality
checks), deciding what is being predicted and how it will be judged (framing, splits), computing
features that a deployed system could also compute (causality), and setting the bar a model must
beat (baselines, metrics). Today you find out which of those you can produce without the page open.

Units covered: `w2d1` SQL I, `w2d2` SQL II, `w2d3` ingestion and data quality, `w2d4` framing and
splits, `w2d5` causal features, `w2d6` baselines and metrics; the project conventions in
[`docs/FLOWGUARD_SPEC.md`](../../docs/FLOWGUARD_SPEC.md) and [`project/README.md`](../../project/README.md).

**Alignment note.** The Week 2 lessons were being written at the same time as this review unit. The
questions below are based on each lesson's stated objective, on the project specification, and on
standard correct content; they will be re-aligned with the final lesson texts (wording, emphasis and
any lesson-specific numbers). If a question refers to something your version of a lesson did not
cover, answer from first principles and note it with `python wb.py note w2d7 "..."`.

## 1. Spaced-review items due today (5-10 minutes)

Open the "Spaced review" list at the top of `progress/notes.md` and answer, closed book, every item
marked due `w2d7`. Check against the `w1d7` answers. Two consecutive *solid* answers remove an item;
otherwise it moves to `w4d7`.

## 2. Retrieval sheet (25 minutes, closed book)

Rules as in `w1d7`: no lessons, handbook, repository or search; two to five sentences each; write
what you would check if you cannot answer; open the key only when all twelve have an attempt.

**SQL (w2d1, w2d2)**

1. Define the *grain* of a table and of a query result. A query joins `customers` to `invoices` and to
   `tickets` and sums `invoices.amount` per customer; the totals are too large for some customers.
   Explain the mechanism and give two structurally different fixes.
2. In `A LEFT JOIN B ON ...`, what is the difference between putting a condition on a column of `B`
   in the `ON` clause and in the `WHERE` clause? Which one silently changes the meaning of the join?
3. For a column with NULLs, what do `COUNT(*)`, `COUNT(col)`, `COUNT(DISTINCT col)` and `AVG(col)`
   each compute? Give one situation where confusing two of them changes a business number.
4. `SUM(x) OVER (PARTITION BY g ORDER BY t)`: what is the default window frame, how does it behave when
   several rows share the same `t`, and how do you make a running total independent of ties? Why can
   a window function not be used in the `WHERE` clause of the same `SELECT`?
5. You have a per-second table `(experiment_id, t, anomaly)` with `anomaly` in {0,1}. Describe, without
   running code, a SQL technique that returns one row per contiguous anomalous segment with its start
   and end. Then say in one sentence what an *as-of join* is and why features need it.

**Data quality and ingestion (w2d3)**

6. Distinguish *data validation* from *model evaluation*. For the SKAB recordings, name three
   different categories of check with one concrete example each, and say what "fail loudly" should
   mean for an ingestion command. Seven SKAB files contain sampling gaps longer than 5 s (the largest
   is 247 s): what should ingestion do about them, and what should it not do?
7. What must an ingestion step record so that someone else can re-run it and know they got the same
   data? Why is the raw data downloaded by script rather than committed?

**Framing and splits (w2d4)**

8. In the project, what is the *unit of prediction* and what is the *unit of independence*? Why are
   splits defined over experiments and not rows, what does the split manifest contain, and why is it
   a versioned file rather than a seed in the training code?
9. Distinguish a point-level label from an event-level label on this dataset. SKAB has about 35 % of
   samples labelled anomalous and 34 events in total. State one consequence of each number for how
   results must be reported.

**Features, baselines, metrics (w2d5, w2d6)**

10. Define a *causal* feature. Give one innocent-looking pandas operation that violates causality and
    one that leaks across the train/test boundary without violating causality. Describe a test that
    can detect look-ahead in a feature function without knowing its implementation.
11. Why establish a trivial baseline before any model? What are the expected ROC AUC and the expected
    average precision (PR AUC) of an uninformative scorer at prevalence `p`? Where must a decision
    threshold be chosen, and why not on the test set?

**Delayed question from Week 1 (w1d5)**

12. A colleague's test reads `assert band_power(x, fs, 8, 12) == pytest.approx(expected, rel=0.2)`
    where `expected` was copied from a notebook run. Name the two independent problems with this
    test and rewrite its *design* (not code) so that it can detect a factor-of-two error.

## 3. Score and choose (10 minutes)

Open [`solutions/lessons/w2d7_review/retrieval_answers.md`](../../solutions/lessons/w2d7_review/retrieval_answers.md)
(question 12's key is also at the end of `solutions/lessons/w1d5_testing_ml_code/assessment_answers.md`).
Mark each answer **solid**, **shaky** or **missing**, exactly as on `w1d7`, and record the lists:

```bash
python wb.py note w2d7 "solid: ...; shaky: ...; missing: ..."
```

## 4. Redo one thing, unassisted (20-30 minutes)

Choose one, in this priority order:

1. a Week 2 lab or challenge whose checks did not pass, or that you passed only with hint 3 or a solution;
2. the diagnostic section you were least satisfied with among `a2_sql`, `a3_cleaning`, `b1_baseline`
   (only if you have already submitted the diagnostic; a redo after submission is practice, and does
   not replace the submitted evidence);
3. the task behind your weakest retrieval answer, for example: write the gaps-and-islands query for
   anomalous segments from scratch; write `validate_splits` and its tests; write a no-look-ahead test
   for a rolling feature.

Protocol (same as `w1d7`)

* Fresh directory or branch, blank file. Do not open your earlier attempt, hints, solutions or the lesson.
* Timer: 25 minutes. Run the unit's checks at most twice.
  ```bash
  python wb.py check w2d5 --challenge      # example
  ```
* Record the conditions, then set the flag the evidence supports:
  ```bash
  python wb.py note w2d2 "redo cold, 25 min, docs only: gaps-and-islands correct, as-of join wrong at ties"
  python wb.py mark w2d2 independent       # only if completion criteria were met under these conditions
  python wb.py mark w2d2 review            # otherwise
  ```

## 5. Interview set 2 (45 minutes, timed)

[`interview/set2_sql_pandas.md`](../../interview/set2_sql_pandas.md): three SQL prompts on the
diagnostic's SQLite database (state the grain before each query; one uses window functions; one is a
retention query with two traps) and one pandas prompt on a point-in-time feature. Self-check with

```bash
python interview/set2_check.py
```

then score against `solutions/interview/set2.md`, including the parts the checker cannot see: did you
state the grain first, and did you look at the data before trusting the first draft?

Compare with set 1: is the dominant error pattern the same kind (not reading the contract, boundary
conditions, running out of time) or a different one? Write one sentence about it in your notes.

## 6. Spaced review and progress flags (5 minutes)

**Spaced-review schedule.** Shaky and missing items from today are due on `w3d7` (one week), then
`w5d7` (two weeks later), then `w8d7`. Items carried from `w1d7` that were not solid today move to
`w4d7`. An item leaves the list after two consecutive solid answers.

```
## Spaced review
- w2d7 Q4 (default window frame, ties) - due w3d7
- w1d7 Q4 (seed vs effect)             - due w4d7   (second miss)
```

**Flags.** Set each from evidence:

```bash
python wb.py status
python wb.py mark w2d1 reading
python wb.py mark w2d1 guided            # lab checks passed (hints allowed)
python wb.py mark w2d1 independent       # challenge or cold redo passed without hints or solutions
python wb.py mark w2d4 review            # shaky or missing today
python wb.py mark w1d4 review off        # a carried item answered solidly twice
python wb.py mark w2d7 guided            # this session done
```

Checklist

- [ ] Due spaced-review items answered before anything else
- [ ] Twelve retrieval answers attempted before opening the key
- [ ] solid / shaky / missing recorded with `wb.py note`
- [ ] One cold redo done and its conditions recorded
- [ ] Interview set 2 attempted under the stated conditions, checked and scored
- [ ] `review` flags and the spaced-review list updated
- [ ] Project check: `splits/v1.json` exists in your project and has not been edited since it was
      frozen (Week 3 depends on it); if you changed it, bump the version instead

Next: Week 3 starts with `w3d1` (leakage: a taxonomy and prevention by construction); see
[roadmap/SCHEDULE.md](../../roadmap/SCHEDULE.md).

---

*Content status and verification: see `STATUS.md`. Interview set 2's reference answers were executed
against the checker and deliberately wrong answers were rejected (details in
`solutions/interview/set2.md`). The retrieval answers are prose; SQL semantics quoted in them
(NULL handling in aggregates, default window frame under ties) were confirmed by execution in SQLite
3.53.1. Statements about the Week 2 lessons await re-alignment as noted above.*
