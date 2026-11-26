---
title: Glossary
parent: Guides
nav_order: 6
---

# Glossary
{: .no_toc }

Each term with an everyday picture first, then the precise meaning and the notebook where the course teaches it.
"Advanced" means the term is covered in the [advanced track](../advanced/).

1. TOC
{:toc}

---

## Tools and data

| Term | Picture | Meaning | Where |
|---|---|---|---|
| **Terminal / shell** | Texting the computer instead of pointing at it | A text interface where you type commands such as `ls`, `cd`, `python` | 03 |
| **Git commit** | A labelled save point in a game | A snapshot of your files with a message, which you can return to | 03 |
| **Relational database** | A set of linked spreadsheets with strict rules | Tables of rows and columns, linked by keys, queried with SQL | 05 |
| **Primary key / foreign key** | A passport number / writing someone's passport number on a form | A column that identifies each row uniquely / a column that refers to another table's primary key | 05 |
| **JOIN** | Matching guests to their table numbers | Combining rows of two tables where a key matches | 07 |
| **Grain** | What one row stands for: one order, or one item in an order | The unit a table's rows describe; mixing grains double-counts | 07 |
| **Window function** | Each runner's position in their own heat | A value computed over related rows without collapsing them, e.g. `ROW_NUMBER() OVER (...)` | 09 |
| **DataFrame** | A spreadsheet you control with code | pandas' table: labelled columns, an index, vectorised operations | 10 |
| **Pipeline** | A recipe card that always runs the steps in order | scikit-learn object chaining preprocessing and a model, fitted on training data only | 15 |
| **Virtual environment** | A separate toolbox for each project | An isolated set of installed Python packages (`python -m venv .venv`) | 29, 37 |
| **Package** | A labelled box instead of loose parts | Importable code with a `pyproject.toml`, installed with `pip install` | 29 |
| **Test / fixture** | A spot check / the test bench it runs on | A function asserting expected behaviour / reusable setup pytest passes into tests | 30 |
| **API / endpoint** | A restaurant counter / one item on its menu | An interface other programs call over HTTP / one URL and method, e.g. `POST /predict` | 34 |
| **Status code** | The waiter's short reply: "here you are", "we don't have that" | The number in an HTTP response: 200 OK, 404 not found, 422 invalid input, 500 server error | 34, 35 |
| **Container image** | A frozen lunchbox; the container is the meal being eaten | A layered filesystem plus a start command; a container is a running instance | 38 |
| **CI** | A gate that checks every delivery | Automated checks (tests, builds) on every push, before anything merges | 39 |

## Modelling and evaluation

| Term | Picture | Meaning | Where |
|---|---|---|---|
| **Baseline** | The bar you have to clear before anyone looks at you | The simplest honest predictor; complexity must beat it by more than the noise | 18 |
| **Threshold** | Where you set the smoke alarm's sensitivity | The score above which you act; chosen from the costs of each kind of mistake | 19 |
| **Leakage** | Seeing the exam answers while revising | Information at training or evaluation time that will not exist, or not in that form, at prediction time | 22 |
| **Group split** | Testing a doctor on patients they have never met | Every row of one unit (customer, machine, experiment) lands on one side of the split | 21 |
| **Temporal split** | Forecasting tomorrow without reading tomorrow's paper | Train on the past, evaluate on the future, never the reverse | 21 |
| **Causal feature** | Driving using only the road you have already passed | A feature at time *t* uses nothing after *t* | 14, 22 |
| **Nested validation** | A referee who did not help pick the team | An outer loop that estimates the whole selection procedure, tuning included | 23 |
| **Bootstrap interval** | Re-drawing the sample many times to see how much the answer wobbles | A range for a metric from resampling the test set; resample whole groups when rows are grouped | 26 |
| **Point vs event metric** | Grading each minute of a fire alarm vs whether each fire was noticed | Per-sample scores vs per-incident detection, delay and false alarms | 28 |
| **Purge / embargo** | A no-man's-land between two fields | Rows dropped around a split boundary so overlapping windows cannot leak | Advanced |

## Serving and operations

| Term | Picture | Meaning | Where |
|---|---|---|---|
| **Model artifact** | A sealed parcel with its packing list | The saved model plus metadata: versions, features, training date, metrics, checksum | 33 |
| **Training/serving skew** | Rehearsing on a different stage from the performance | The served model computes its inputs differently from the evaluated one | Advanced |
| **Least privilege** | A key that opens only the rooms you need | Giving a user or service only the permissions its job requires | 41 |
| **Rollback** | The undo button that must already be tested | Pointing production back at the previous known-good version | 41, 43 |
| **p95 latency** | The wait 1 in 20 customers exceeds | 95th percentile of response time; averages hide the slow tail | 42 |
| **Golden signals** | Pulse, temperature, breathing, blood pressure | Traffic, errors, latency and saturation of a service | 42 |
| **Drift** | The river moved; the boat may be fine | A change in the input distribution (measured, e.g., with PSI) | 43 |
| **Degradation** | The boat is leaking | A measured loss of performance, which needs labels | 43 |
| **Canary / shadow** | A taster before the banquet / a dress rehearsal | A new model on a small live share / scoring in parallel without serving | 43 |
| **Idempotent** | Pressing a lift button twice still calls one lift | Repeating an operation has the same effect as doing it once | Advanced |
| **Graceful degradation** | Stairs when the lift breaks, with a sign saying so | A simpler explicit fallback, flagged in the response, never silent | Advanced |

## Course vocabulary

| Term | Meaning |
|---|---|
| **Lesson / lab** | A notebook that teaches (three a week) / a graded assignment combining the week (one a week) |
| **Exercise key** | The name the grader uses, e.g. `w02.cheap_products` (week 2) |
| **Solved copy** | The same notebook with every exercise filled in, in `solutions/notebooks/` |
| **Progress flags** | `reading`, `guided`, `independent`, `review`, stored in `progress/progress.json` |
| **Frozen split** | `v2.json`: the project's fixed split of SKAB experiments (7 test, 27 development) |
| **SYNTHETIC** | Generated data; it supports conclusions about code and reasoning, not about real-world model quality |
