---
title: "Week 9 · Serving models"
parent: Weekly plan
nav_order: 9
---

# Week 9 · Serving models

**Goal:** save models safely and serve predictions through a tested FastAPI service.

Until now your models lived only inside a notebook. This week they leave it. You save the churn pipeline as a
**bundle** (the model file plus metadata and a checksum), learn why a model file must never come from an untrusted
source, and run a **batch job** that scores a file of customers while rejecting bad rows with a reason. Then you
learn HTTP from zero and put the model behind a **FastAPI** service with validated input and output, test it the
way a code reviewer would (including tests that must catch planted bugs), and make its failures clear and safe.
The project milestone puts the SKAB fault detector behind `POST /score`. Everything runs in Google Colab: APIs are
called in-process with `TestClient`, so no server or open port is needed.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 33 | Saving models and batch prediction | lesson | 90 min | [read](../notebooks/33_saving_models_batch.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/33_saving_models_batch.ipynb) |
| 34 | APIs and FastAPI | lesson | 100 min | [read](../notebooks/34_apis_and_fastapi.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/34_apis_and_fastapi.ipynb) |
| 35 | Testing APIs and handling bad input | lesson | 90 min | [read](../notebooks/35_testing_apis_bad_input.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/35_testing_apis_bad_input.ipynb) |
| 36 | Project milestone 2: a prediction API | lab | 120 min | [read](../notebooks/36_project_m2_prediction_api.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/36_project_m2_prediction_api.ipynb) |

## Before you start

* Weeks 4-5: the churn table and a scikit-learn pipeline (`fit`, `predict_proba`, thresholds).
* Week 7: project milestone 1 (notebook 28), the burn-in z-score detector on SKAB.
* Week 8: functions in files, `%%writefile`, and pytest basics (`assert`, test functions, fixtures).
* No web or HTTP experience is assumed.

## What you will be able to do

* save and load a fitted pipeline with `joblib`, and explain why loading a pickle/joblib file can run code;
* compute and verify a SHA-256 checksum, and refuse a bundle that changed or was saved with another
  scikit-learn version;
* write a batch prediction job that stops on missing columns and reports rejected rows instead of guessing;
* explain requests, responses, methods, status codes and JSON, and read a 422 error;
* build a FastAPI app with `GET /health` and `POST /predict`, using pydantic models for input and output;
* write a standalone service file that loads its model once from a configurable location;
* test an API on the happy path and on bad input, and show that your tests catch planted bugs;
* return 503 when the model is missing and a short 500 when it crashes, with one consistent error format;
* serve the project's detector behind `POST /score`, check parity with the batch code, and state its limits.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 33, sections 0-2 (joblib, why model files are code, checksums) | 45 min |
| 2 | Notebook 33, sections 3-4 and quiz (bundles, the batch job) | 1 h |
| 3 | Notebook 34, sections 1-3 (HTTP, a first app, path parameters) | 50 min |
| 4 | Notebook 34, sections 4-6 and quiz (pydantic, `/predict`, the service file) | 1 h |
| 5 | Notebook 35 (testing the API, bad input, safe failures, a pytest file) | 1.5 h |
| 6 | Notebook 36, the project milestone, without looking at the solutions | 2 h |
| 7 | Review: re-read the FastAPI guide's cheat sheet; redo any exercise you needed a hint for | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top, and later cells
still work if you skipped an exercise (they say when they used the course's reference version). Files written this
week go to `runs/week09/`, which Git ignores.

## Tool guides

* [FastAPI and pydantic](../tools/fastapi.html): HTTP in five minutes, endpoints, `TestClient`, pydantic models
  and validators, loading a model once, helpful errors, testing, common errors and a cheat sheet.
* [pytest](../tools/pytest.html), from Week 8, for fixtures and `parametrize`.
* [Python packaging](../tools/packaging.html), from Week 8, for turning the service into an installable package.

Next week: [Week 10 · Containers and CI](week-10.html).
