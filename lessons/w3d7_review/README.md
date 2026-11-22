# w3d7 - Week 3 review and catch-up (light day)

**Time budget: 60-90 minutes.** No new material.

| Activity | Time |
|---|---|
| 1. Spaced-review items due today (from `w2d7`) | 5-10 min |
| 2. Retrieval sheet, from memory | 25 min |
| 3. Score it; choose what to redo | 10 min |
| 4. Redo one thing, cold and unassisted | 20-30 min |
| 5. Interview set 3 (timed, spoken) | 45 min, or the short form (30 min) |
| 6. Update progress flags and the spaced-review list | 5 min |

On a 60-minute day: activities 1-3, then either 4 or the short form of 5, then 6.

## Purpose

Week 3 was about one question: *how much should anyone believe a reported number?* You classified
the ways information leaks into an evaluation, designed validation that matches how a detector is
deployed, kept selection out of the final estimate, separated point-level from event-level
performance, attached intervals that respect the independent unit, and turned errors into a ranked
list. These are the topics interviewers probe hardest in a candidate from research, because they
are where strong modellers most often fool themselves. Today you find out what you can say about
them without the page open, and for the first time you say it **aloud**.

Units covered: `w3d1` leakage, `w3d2` group and temporal validation, `w3d3` hyperparameter and
threshold selection, `w3d4` point versus event evaluation, `w3d5` uncertainty, `w3d6` error analysis
and the timed transfer exercise; the amendments at the end of
[`docs/FLOWGUARD_SPEC.md`](../../docs/FLOWGUARD_SPEC.md) and the findings in
[`project/README.md`](../../project/README.md).

**Alignment note.** The Week 3 lessons were being written at the same time as this review unit. The
questions are based on each lesson's stated objective, on the project specification and findings,
and on standard correct content; they will be re-aligned with the final lesson texts (wording,
emphasis, lesson-specific numbers and the exact event-matching convention of `w3d4`). If a question
refers to something your version of a lesson did not cover, answer from first principles and note it
with `python wb.py note w3d7 "..."`.

## 1. Spaced-review items due today (5-10 minutes)

Open the "Spaced review" list at the top of `progress/notes.md` and answer, closed book, every item
marked due `w3d7`. Check against the `w2d7` (or `w1d7`) answers. Two consecutive *solid* answers
remove an item; otherwise it moves to `w5d7`.

## 2. Retrieval sheet (25 minutes, closed book)

Rules as before: no lessons, handbook, repository or search; two to five sentences each; if you
cannot answer, write what you would check; open the key only when all twelve have an attempt.

**Leakage (w3d1)**

1. Name five distinct kinds of leakage and give a one-line example of each. Which of them does an
   experiment-wise (grouped) split prevent, and which does it leave untouched?
2. "Prevention by construction": what does putting preprocessing inside a scikit-learn `Pipeline`
   guarantee, and which steps must be inside it? Name one leak a pipeline cannot prevent.
3. In SKAB, 1,290 rows appear in two files each and 235 of them carry contradictory labels. State
   two separate consequences: one for how splits must be built, one for what any model can achieve.
   Why was the answer a manifest `v2` and not an edit of `v1`?

**Validation design (w3d2)**

4. Grouped validation, temporal (forward-chaining) validation, and the combination: say what
   deployment question each one answers. Which matches "a detector trained on past experiments is
   run on a new experiment", and which matches "the same machine next month"?
5. What are *purging* and an *embargo*, when are they needed, and how large must the gap be? Why
   does the experiment-wise protocol of this project mostly not need them, and when would it?

**Selection (w3d3)**

6. In nested cross-validation, what does the inner loop do, what does the outer score estimate,
   and which model do you ship? Why is the best inner score not a performance estimate?
7. A decision threshold is described in this course as "a fitted parameter". Explain, and say
   roughly how the optimism from selecting among `K` candidates on the same data grows with `K`.

**Point versus event evaluation (w3d4)**

8. Define event recall, detection delay and false alarms per hour. Give one detector that scores
   well at point level and badly at event level, and one with the opposite profile. Why must delay
   be measured in seconds and not rows on this dataset?

**Uncertainty (w3d5)**

9. Describe a cluster bootstrap for a metric computed on the 7 test experiments of the frozen split:
   what is resampled, what is recomputed, what is reported. Why is resampling rows wrong here, and
   what is still doubtful about an interval built from 7 clusters?
10. Two models are scored on the same test experiments. Why compare them with a *paired* procedure,
    and what exactly is the quantity whose interval you report? When the interval for the
    difference contains zero, what do you write in the report?

**Error analysis (w3d6)**

11. What turns a list of errors into an error *analysis*? Describe the steps from raw misses and
    false alarms to a ranked failure taxonomy, and name the way error analysis itself can leak.

**Delayed question from Week 2 (w2d1)**

12. On the maintenance database of `w2d1`, `SELECT * FROM sites WHERE site_id NOT IN (SELECT site_id
    FROM technicians)` returns no rows, although you can see sites that have no technician. Give the
    mechanism and two correct rewrites.

## 3. Score and choose (10 minutes)

Open [`solutions/lessons/w3d7_review/retrieval_answers.md`](../../solutions/lessons/w3d7_review/retrieval_answers.md).
Mark each answer **solid**, **shaky** or **missing** and record the lists:

```bash
python wb.py note w3d7 "solid: ...; shaky: ...; missing: ..."
```

## 4. Redo one thing, unassisted (20-30 minutes)

Choose one, in this priority order:

1. a Week 3 lab or challenge whose checks did not pass, or that you passed only with hint 3 or a solution;
2. the transfer exercise of `w3d6`, if you did not finish it inside its 90 minutes: redo only the
   part you ran out of time for, and record that it is a redo;
3. the task behind your weakest retrieval answer, for example: write `extract_events` and an event
   matcher with tests from a blank file; write a cluster bootstrap for a per-experiment metric;
   write the permutation demonstration that feature selection outside cross-validation invents accuracy.

Protocol (unchanged)

* Fresh directory or branch, blank file. No earlier attempt, hints, solutions or lesson text.
* Timer: 25 minutes. Run the unit's checks at most twice.
  ```bash
  python wb.py check w3d4 --challenge      # example
  ```
* Record the conditions, then set the flag the evidence supports:
  ```bash
  python wb.py note w3d5 "redo cold, 25 min, docs only: cluster bootstrap correct; paired difference resampled rows by mistake"
  python wb.py mark w3d5 independent       # only if completion criteria were met under these conditions
  python wb.py mark w3d5 review            # otherwise
  ```

## 5. Interview set 3 (45 minutes, timed, spoken)

[`interview/set3_validation_fundamentals.md`](../../interview/set3_validation_fundamentals.md): five
"spot the flaw and fix it" scenarios, three fundamentals to explain or derive, and one coding prompt
(grouped K-fold from scratch).

This is the first set under the Weeks 3-5 conditions, and two things change:

* **You speak the answers.** Record them or talk while writing bullet notes. Saying "the mechanism
  is ..." out loud exposes gaps that silent reading of your own notes hides.
* **Rubric first, worked answers later.** After the attempt, open only part A of
  `solutions/interview/set3.md` and score yourself. Make a second attempt at anything below
  "Demonstrated" before reading part B.

```bash
python -m pytest interview/set3_tests -q        # the coding prompt
```

Compare with sets 1 and 2: for the scenarios, was the weak part naming the flaw, explaining the
mechanism, or proposing the fix? Write one sentence about it in your notes.

## 6. Spaced review and progress flags (5 minutes)

**Spaced-review schedule.** Shaky and missing items from today are due on `w4d7` (one week), then
`w6d7`, then `w8d7`. Items carried from `w2d7` that were not solid today move to `w5d7`. An item
leaves the list after two consecutive solid answers.

```
## Spaced review
- w3d7 Q9 (cluster bootstrap, 9 clusters) - due w4d7
- w2d7 Q4 (default window frame, ties)    - due w5d7   (second miss)
```

**Flags.** Set each from evidence:

```bash
python wb.py status
python wb.py mark w3d1 reading
python wb.py mark w3d1 guided            # lab checks passed (hints allowed)
python wb.py mark w3d1 independent       # challenge or cold redo passed without hints or solutions
python wb.py mark w3d5 review            # shaky or missing today
python wb.py mark w3d7 guided            # this session done
```

Checklist

- [ ] Due spaced-review items answered before anything else
- [ ] Twelve retrieval answers attempted before opening the key
- [ ] solid / shaky / missing recorded with `wb.py note`
- [ ] One cold redo done and its conditions recorded
- [ ] Interview set 3 attempted aloud; scored against part A; second attempts made before part B
- [ ] `review` flags and the spaced-review list updated
- [ ] Project check: your split manifest is `v2` (overlap groups kept together), your results table
      contains the elapsed-time baseline, and every reported metric names its unit of resampling

Next: Week 4 starts with `w4d1` (time-series fundamentals and forecast-residual detectors); see
[roadmap/SCHEDULE.md](../../roadmap/SCHEDULE.md).

---

*Content status and verification: see `STATUS.md`. Interview set 3's coding reference was executed
against its tests and deliberately wrong answers were rejected; the numbers in its worked answers
were simulated or computed (details in `solutions/interview/set3.md`). The retrieval answers are
prose; the SQL behaviour in answer 12 and the numerical facts in answers 7 and 9 were confirmed by
execution. Statements about the Week 3 lessons await re-alignment as noted above.*
