---
title: "Week 12 · Capstone and career"
parent: Weekly plan
nav_order: 12
---

# Week 12 · Capstone and career

**Goal:** finish and present the project, and practise for interviews.

This week brings the course together. You assemble the SKAB fault-detection project end to end in one notebook,
with one split, one detector definition and one scoring function, and numbers that all come from code you can
re-run. Then you turn those numbers into the three documents that carry a project (a README, a short technical
report and a model card), practise the common interview formats, and take the final assessment. Everything runs
in Google Colab.

The project is an **educational prototype** on laboratory recordings. Finishing this course, or this week, does
not make anyone job-ready by itself; what it gives you is a finished, honest project and a clear picture of what
to practise next.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 45 | Capstone: finish the project end to end | lesson | 120 min | [read](../notebooks/45_capstone_build.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/45_capstone_build.ipynb) |
| 46 | Communicating results: README, report, model card | lesson | 90 min | [read](../notebooks/46_communicating_results.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/46_communicating_results.ipynb) |
| 47 | Interview preparation: SQL, Python, ML, system design | lesson | 120 min | [read](../notebooks/47_interview_preparation.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/47_interview_preparation.ipynb) |
| 48 | Final assessment | lab | 120 min | [read](../notebooks/48_final_assessment.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/48_final_assessment.ipynb) |

## Before you start

* The three project milestones: notebooks 28 (evaluation), 36 (prediction API) and 44 (monitoring). Notebook 45
  rebuilds every piece in a few lines, so an unfinished milestone does not block you.
* Weeks 2-3 (SQL), 5-7 (metrics, validation, uncertainty), 8 (pytest), 9 (pydantic and FastAPI) and 11 (drift):
  the final assessment draws on all of them.
* Basic Markdown: headings with `#`, bullets with `-`, code blocks between three backticks (notebook 46 shows each).

## What you will be able to do

* assemble a project from a checklist: frozen split, causal scores, evaluation, saved detector, scoring function,
  monitoring summary;
* report point and event metrics with a bootstrap over experiments, and use an exact interval when the bootstrap
  collapses (7 of 7 detected means "at least about 0.59", not "100%");
* save a detector with metadata and a checksum, and serve exactly what was evaluated;
* write a README, a technical report and a model card in which every number has an interval and every claim stays
  inside the evidence, and check them automatically;
* approach timed SQL and Python questions with a routine, explain core ML concepts briefly, structure an ML system
  design answer, and tell a project story in the STAR format;
* judge your own level across the course and choose what to practise next.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 45, steps 0-3 (checklist, split, scores, evaluation with intervals) | 1 h |
| 2 | Notebook 45, steps 4-6 and quiz (saved detector, scoring function, monitoring summary) | 1 h |
| 3 | Notebook 46 (three documents; write your own README, report and model card) | 1.5 h |
| 4 | Notebook 47, sections 1-4 (SQL and Python against a timer, ML concepts) | 1 h |
| 5 | Notebook 47, sections 5-6 and quiz (system design, STAR); say your answers out loud | 1 h |
| 6 | Notebook 48, the final assessment, in one sitting, without the solutions | 2 h |
| 7 | Self-assessment: pick your two weakest areas and plan the next month | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top, and later cells
still work if you skipped an exercise (they say when they used the course's reference version). Files written this
week go to `runs/week12/`, which Git ignores.

## Tool guides

No new tools this week. The ones you will reach for most:

* [SQL (SQLite)](../tools/sql.html) and [pandas](../tools/pandas.html) for the timed questions;
* [scikit-learn](../tools/scikit-learn.html), [pytest](../tools/pytest.html) and
  [FastAPI and pydantic](../tools/fastapi.html) for the final assessment;
* [Git and GitHub](../tools/git-github.html) to publish your capstone repository.

Previous week: [Week 11 · Deploy and operate](week-11.html). For more depth on any topic, continue with the
[advanced track](../advanced/index.html).
