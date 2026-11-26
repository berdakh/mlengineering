---
title: "Week 11 · Deploy and operate"
parent: Weekly plan
nav_order: 11
---

# Week 11 · Deploy and operate

**Goal:** deploy safely, log and monitor a model service, and tell input drift from real degradation.

A model that answers requests all day needs three things you have not built yet: a safe way to put it somewhere
other programs can reach, records of what it does, and a way to notice when the world changes under it. This week
you prepare an AWS deployment the careful way (identity, secrets, a configuration check, a least-privilege policy,
a cost estimate, rollback), without creating anything or spending money. Then you log every prediction as
structured JSON, turn the log into metrics, a dashboard and alerts, and learn why a drift alarm and a drop in
quality are different events that need different responses. The project milestone builds a monitoring demo for
the SKAB detector. Everything runs in Google Colab; no cloud account is needed.

| # | Notebook | Kind | Time | Open |
|---|---|---|---|---|
| 41 | Deploying to the cloud safely | lesson | 90 min | [read](../notebooks/41_cloud_deployment_basics.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/41_cloud_deployment_basics.ipynb) |
| 42 | Logging and monitoring a model service | lesson | 90 min | [read](../notebooks/42_logging_monitoring.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/42_logging_monitoring.ipynb) |
| 43 | Drift, degradation and model updates | lesson | 100 min | [read](../notebooks/43_drift_and_updates.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/43_drift_and_updates.ipynb) |
| 44 | Project milestone 3: monitoring demo | lab | 120 min | [read](../notebooks/44_project_m3_monitoring.html) · [Colab](https://colab.research.google.com/github/berdakh/mlengineering/blob/main/notebooks/44_project_m3_monitoring.ipynb) |

## Before you start

* Week 5: recall and precision. Week 6: why a test set is a one-time estimate.
* Week 9: the FastAPI service, model versions in responses, status codes 200 / 422 / 500.
* Week 10: Docker images and CI (the image is what a cloud service runs).
* Project milestones 1 and 2 (notebooks 28 and 36): the burn-in z-score detector on SKAB.
* No cloud or monitoring experience is assumed.

## What you will be able to do

* explain what a deployment involves, and when to choose a virtual machine, a container service or serverless;
* explain users, roles, temporary credentials and least privilege, and where secrets may live;
* find hard-coded secrets, check a deployment configuration, and write and lint a least-privilege IAM policy;
* estimate a monthly bill from unit prices, and pick a rollback target from a release history;
* log predictions as JSON lines without personal data, with Python's `logging` and a JSON formatter;
* compute traffic, error rate, latency percentiles and prediction rate per window, and draw a dashboard;
* write alert rules with thresholds and durations that fire only when a person must act;
* measure input drift with PSI and KS, explain why window size matters, and measure recall with delayed labels;
* tell drift from degradation, and update a model through shadow, canary and rollback;
* monitor the SKAB detector: a log, a drift table with a sensible reference, an ops table, a dashboard and a note.

## Suggested pacing (6-8 hours)

| Session | Work | Time |
|---|---|---|
| 1 | Notebook 41, sections 1-3 (deployment options, identity, secrets) | 45 min |
| 2 | Notebook 41, sections 4-6 and quiz (configuration checks, policies, cost, rollback) | 50 min |
| 3 | Notebook 42, sections 1-3 (structured logs, the logging module, metrics) | 50 min |
| 4 | Notebook 42, sections 4-5 and quiz (dashboard, alerts) | 40 min |
| 5 | Notebook 43 (drift statistics, delayed labels, shadow and canary) | 1 h 40 min |
| 6 | Notebook 44, the project milestone, without looking at the solutions | 2 h |
| 7 | Review: re-read the two tool guides' cheat sheets; redo any exercise you needed a hint for | 30 min |

If a session runs long, stop at the end of a section: every notebook can be re-run from the top, and later cells
still work if you skipped an exercise (they say when they used the course's reference version). Files written this
week go to `runs/week11/`, which Git ignores.

**About real cloud deployments.** The course never asks you to create cloud resources. If you decide to deploy the
API for real, follow the [cloud tool guide](../tools/cloud-aws.html) only after setting a budget alert, estimating
the bill and writing down the teardown commands, and delete everything when you are done.

## Tool guides

* [Cloud basics (AWS)](../tools/cloud-aws.html): accounts, IAM and roles, the AWS CLI with single sign-on,
  secrets, policies, an ECR + ECS on Fargate path step by step with teardown, cost estimation, common errors.
* [Logging and monitoring](../tools/monitoring.html): the `logging` module, JSON lines, what to log and what not
  to, metrics, dashboards, alerts, drift statistics, safe updates, common errors and a cheat sheet.
* [Docker](../tools/docker.html), from Week 10, for the image a cloud service runs.

Next week: [Week 12 · Capstone and career](week-12.html).
