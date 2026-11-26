---
title: "How the course is designed"
parent: Guides
nav_order: 9
---

# How the course is designed
{: .no_toc }

The binding details (notebook layout, grader rules, quality bar) are in the
[course specification](../maintainers/course-spec.html). This page explains the choices behind them.

1. TOC
{:toc}

---

## Who it is for, and the gap it fills

An introductory machine-learning course teaches *why* models generalise: training vs test error, overfitting,
regularisation, validation. It usually stops at a clean dataset in a notebook. Teams spend most of their time on
everything around that: getting data out of a database, cleaning it, making features that do not leak, checking
that a result is real, and turning a model into a service that someone can rely on.

The course is for students who have the first part and none of the second. It assumes intro-ML ideas and basic
Python, and assumes **no** industry tool: SQL, Git, pytest, packaging, APIs, Docker, CI and the cloud all start
from zero. Wherever a lesson touches modelling it connects back to what the student already knows ("in
*Learning from Data* terms, the test set is a one-time estimate of E_out") and then shows what changes with real,
messy data.

## The arc of twelve weeks

| Weeks | Theme | Why in this order |
|---|---|---|
| 1 | Workbench: Colab, Python, terminal, Git | Every later week uses them |
| 2-3 | SQL, then pandas and data quality | Data comes before models; SQL is the most-asked skill and the most unfamiliar |
| 4 | Exploratory analysis, features, pipelines | Turning tables into model inputs, without leakage, by construction |
| 5-6 | Framing, baselines, metrics; validation and leakage | The theory the student knows, applied to a business problem where it is easy to fool yourself |
| 7 | Model comparison with uncertainty, error analysis; project starts | Choosing a model on evidence, then a real dataset |
| 8 | Packages, tests, configuration, logging | Code someone else can run and trust |
| 9 | Saved models, FastAPI, API tests; project milestone 2 | A model becomes a service |
| 10 | VS Code, Docker, GitHub Actions | The move to a local, reproducible setup |
| 11 | Cloud deployment (prepared, not run), monitoring, drift; project milestone 3 | Operating a model, safely and without spending money |
| 12 | Capstone, communication, interviews, final assessment | Finishing, explaining, and checking what has landed |

Two running threads tie the weeks together: an **online-shop dataset** (synthetic, in `data/course/shop.db`) used
for SQL, pandas and a churn model in Weeks 2-6, and the **SKAB fault-detection project** on real sensor data in
notebooks 28, 36, 44 and 45 ([project guide](project.html)).

## The teaching pattern

Every lesson is one notebook of 75-120 minutes, built from 4-6 short sections. Each section goes **Why** (the
problem on the job) → **Idea** (one concept, plain language, a diagram where it helps, at most about 350 words
before the student types) → **See it** (a worked example that runs) → **Try it** (a small edit, predicting the
result first) → **Exercise** (graded). Lessons end with a quiz, a recap, an "on the job" paragraph and links to
the tool guide, the handbook and the advanced track.

The pattern follows a few well-established ideas about learning a practical skill alone: short explanations
before practice, worked examples before independent problems, immediate feedback, and retrieval (quizzes and
labs) rather than re-reading.

Each week ends with a **lab**: 5-8 graded exercises that combine the week on one realistic task, with no new
concepts. A **tool guide** accompanies every tool, as a self-contained reference to return to later.

## Grading inside the notebook

Exercises are graded by the cell under them (`grade("w02.cheap_products", query)`), with tests in
`src/mlcourse/graders/`. The rules:

* Graders check **behaviour on several inputs**, including edge cases (empty input, missing values, ties), never one
  exact implementation or query text. SQL answers are compared with an independently computed result.
* Failure messages explain **what** is wrong ("you included products that cost exactly 15"), never the answer.
* When students write tests, the grader runs those tests against correct code (they must pass) and against
  several planted bugs (they must fail).
* Everything runs offline in a second or two, so Colab is enough.

Solved copies of every notebook are generated from the same source and kept in `solutions/notebooks/`.

## How the material is checked

`tools/verify_notebooks.py` executes both copies of each notebook: the solved copy must pass every grader with
no cell errors, and the student copy must fail every grader, raising nothing but `NotImplementedError`. That
proves each exercise is gradable and that the starter does not already pass. What it cannot prove is that a
lesson teaches well; see the [status page](status.html).

## Relation to the advanced track

The [advanced track](../advanced/) is the earlier, denser 48-session program written for people who already train
models and want research-grade evaluation and full engineering on the same SKAB project. It assumes much more
(comfortable Python, a terminal, independent work against file-based lab checks), so it now follows this course
instead of replacing it. Its design is described in [How the advanced track is designed](../advanced/design.html).
