---
title: "Week 2 · Data: SQL, pandas, quality, features, baselines"
parent: Weekly plan
nav_order: 2
---

# Week 2 — Data: SQL, pandas, quality, features, baselines
{: .no_toc }

**Goal:** by the end of the week you can get the project data in through checked, reproducible steps, frame the problem, and beat it with honest baselines.

1. TOC
{:toc}

---

Six core days of about **2 hours** each (plus an optional hour), and one lighter review day. Every core day is one notebook: read it on this site, run it in Colab, or open it in Jupyter.

## Schedule

| Day | Session | Notebook | Deliverable |
|---|---|---|---|
| 1 | **SQL I: grain, joins, aggregation and NULL semantics** | [`07_sql_joins_grain`](../notebooks/07_sql_joins_grain.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/07_sql_joins_grain.ipynb) | Solved query set with a stated grain for every result; fan-out bug report on a broken query. |
| 2 | **SQL II: CTEs, window functions and time-series queries** | [`08_sql_windows_timeseries`](../notebooks/08_sql_windows_timeseries.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/08_sql_windows_timeseries.ipynb) | Query set + pandas equivalence tests; a point-in-time-correct feature query. |
| 3 | **pandas ingestion, schemas and data-quality checks (project data arrives)** | [`09_data_quality_ingestion`](../notebooks/09_data_quality_ingestion.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/09_data_quality_ingestion.ipynb) | `flowguard ingest` command, data dictionary, data-quality report, provenance record (source, licence, hashes). |
| 4 | **Problem framing and versioned split definitions** | [`10_problem_framing_splits`](../notebooks/10_problem_framing_splits.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/10_problem_framing_splits.ipynb) | Problem statement, label definition, `splits/v1.json` manifest with a leakage-safety test. |
| 5 | **Reproducible feature generation without look-ahead** | [`11_feature_pipeline`](../notebooks/11_feature_pipeline.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/11_feature_pipeline.ipynb) | Feature pipeline with no-look-ahead tests and content-addressed outputs. |
| 6 | **Strong simple baselines and metrics that match the decision** | [`12_baselines_metrics`](../notebooks/12_baselines_metrics.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/12_baselines_metrics.ipynb) | Baseline table for the project (trivial, threshold, linear); transfer exercise part 1 baseline. |
| 7 | **Review and catch-up (light)** | [review below](#day-7--review-and-catch-up) | Week 2 retrieval sheet; interview set 2 (SQL + pandas, timed). |

## What each day is for

**Day 1 — SQL I: grain, joins, aggregation and NULL semantics.** Write correct multi-table queries by reasoning about table grain first; recognise fan-out, NULL and anti-join traps. *Prerequisites:* Diagnostic a2 reviewed.

**Day 2 — SQL II: CTEs, window functions and time-series queries.** Use window functions for ranking, running statistics, gaps-and-islands and as-of joins on event and sensor tables; reproduce each result in pandas. *Prerequisites:* w2d1.

**Day 3 — pandas ingestion, schemas and data-quality checks (project data arrives).** Ingest the project dataset through a documented, re-runnable step with explicit schema and quality checks expressed as code that fails loudly. *Prerequisites:* w1d6; diagnostic a3 reviewed.

**Day 4 — Problem framing and versioned split definitions.** Translate the stakeholder problem into an ML task: unit of prediction, label definition (point vs event), costs of errors, constraints; freeze splits by experiment and time in a versioned manifest. *Prerequisites:* w2d3.

**Day 5 — Reproducible feature generation without look-ahead.** Build causal rolling-window features and train-only statistics as a deterministic, cached, tested pipeline step. *Prerequisites:* w2d4, w1d5.

**Day 6 — Strong simple baselines and metrics that match the decision.** Establish trivial and classical baselines and choose metrics from the decision (imbalance, PR vs ROC, thresholds, calibration basics) on the project data and on an unfamiliar business table. *Prerequisites:* w2d5; diagnostic b1 reviewed.

## Day 7 — review and catch-up

A lighter day: retrieval practice from memory, one unassisted redo, and a timed interview set. It is also the buffer if a core day ran over.


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

### Purpose

Week 2 moved from code structure to data: getting the right rows (SQL), trusting them (quality
checks), deciding what is being predicted and how it will be judged (framing, splits), computing
features that a deployed system could also compute (causality), and setting the bar a model must
beat (baselines, metrics). Today you find out which of those you can produce without the page open.

Units covered: `w2d1` SQL I, `w2d2` SQL II, `w2d3` ingestion and data quality, `w2d4` framing and
splits, `w2d5` causal features, `w2d6` baselines and metrics; the project conventions in
[`docs/maintainers/flowguard-spec.md`](../maintainers/flowguard-spec.html) and [`docs/guides/project.md`](../guides/project.html).

The questions were re-aligned with the final Week 2 lessons on 2026-11-21; numbers quoted from the
project data are the ones those lessons report.

### 1. Spaced-review items due today (5-10 minutes)

Open the "Spaced review" list at the top of `progress/notes.md` and answer, closed book, every item
marked due `w2d7`. Check against the `w1d7` answers. Two consecutive *solid* answers remove an item;
otherwise it moves to `w4d7`.

### 2. Retrieval sheet (25 minutes, closed book)

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
   mean for an ingestion command. Six SKAB files contain sampling gaps longer than 5 s (nine gaps, the
   largest 247 s): what should ingestion do about them, what should it not do, and is this an *error*
   or a *warning*?
7. What must an ingestion step record so that someone else can re-run it and know they got the same
   data? Why is the raw data downloaded by script rather than committed?

**Framing and splits (w2d4)**

8. In the project, what is the *unit of prediction* and what is the *unit of independence*? Why are
   splits defined over experiments and not rows (recall the size of the gap `w2d4` measured), what
   does the split manifest contain, and why is it a versioned file rather than a seed in the
   training code?
9. Distinguish a point-level label from an event-level label on this dataset. SKAB has about 35 % of
   samples labelled anomalous and 34 events in total. State one consequence of each number for how
   results must be reported.

**Features, baselines, metrics (w2d5, w2d6)**

10. Define a *causal* feature. Give one innocent-looking pandas operation that violates causality and
    one that leaks across the train/test boundary without violating causality. Describe a test that
    can detect look-ahead in a feature function without knowing its implementation. In `w2d5`, which
    mattered more for the offline score on SKAB: centring the window, or the choice of reference rows
    for normalisation? What follows from each answer?
11. Why establish a trivial baseline before any model? What are the expected ROC AUC and the expected
    average precision (PR AUC) of an uninformative scorer at prevalence `p`? Where must a decision
    threshold be chosen, and why not on the test set? In `w2d6` a scorer that uses only elapsed time
    and no sensor reached a higher test F1 than every sensor baseline: what does that tell you about
    the dataset, and what must it change in the project?

**Delayed question from Week 1 (w1d5)**

12. A colleague's test reads `assert band_power(x, fs, 8, 12) == pytest.approx(expected, rel=0.2)`
    where `expected` was copied from a notebook run. Name the two independent problems with this
    test and rewrite its *design* (not code) so that it can detect a factor-of-two error.

### 3. Score and choose (10 minutes)

Open [`solutions/labs/w2d7_review/retrieval_answers.md`](https://github.com/berdakh/mlengineering/blob/main/solutions/labs/w2d7_review/retrieval_answers.md)
(question 12's key is also at the end of `solutions/labs/w1d5_testing_ml_code/assessment_answers.md`).
Mark each answer **solid**, **shaky** or **missing**, exactly as on `w1d7`, and record the lists:

```bash
python wb.py note w2d7 "solid: ...; shaky: ...; missing: ..."
```

### 4. Redo one thing, unassisted (20-30 minutes)

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

### 5. Interview set 2 (45 minutes, timed)

[`interview/set2_sql_pandas.md`](https://github.com/berdakh/mlengineering/blob/main/interview/set2_sql_pandas.md): three SQL prompts on the
diagnostic's SQLite database (state the grain before each query; one uses window functions; one is a
retention query with two traps) and one pandas prompt on a point-in-time feature. Self-check with

```bash
python interview/set2_check.py
```

then score against `solutions/interview/set2.md`, including the parts the checker cannot see: did you
state the grain first, and did you look at the data before trusting the first draft?

Compare with set 1: is the dominant error pattern the same kind (not reading the contract, boundary
conditions, running out of time) or a different one? Write one sentence about it in your notes.

### 6. Spaced review and progress flags (5 minutes)

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
      frozen; if you changed it, bump the version instead. (`w3d1` supersedes it with a `v2` that keeps
      experiments sharing duplicated rows together; see `docs/guides/project.md`.)

Next: Week 3 starts with `w3d1` (leakage: a taxonomy and prevention by construction); see
[roadmap/SCHEDULE.md](../guides/schedule.html).

---

*Content status and verification: see `STATUS.md`. Interview set 2's reference answers were executed
against the checker and deliberately wrong answers were rejected (details in
`solutions/interview/set2.md`). The retrieval answers are prose; SQL semantics quoted in them
(NULL handling in aggregates, default window frame under ties) were confirmed by execution in SQLite
3.53.1. Project numbers are quoted from the Week 2 lessons, which report runs on the real SKAB files.*

**Next session:** [w3d1_leakage](../notebooks/13_leakage.html).

