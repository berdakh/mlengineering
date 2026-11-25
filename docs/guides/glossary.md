---
title: Glossary
parent: Guides
nav_order: 7
---

# Glossary
{: .no_toc }

## In plain terms

Each term with an everyday picture first, then the precise meaning and where the course teaches it.

| Term | Picture | Meaning | Where |
|---|---|---|---|
| **Leakage** | Seeing the exam answers while revising | Information at training or evaluation time that will not exist, or not in that form, at prediction time | 13 |
| **Group split** | Testing a doctor on patients they have never met | Every row of one unit (subject, machine, experiment) lands on one side of the split | 10, 14 |
| **Temporal split** | Forecasting tomorrow without reading tomorrow's paper | Train on the past, evaluate on the future, never the reverse | 14 |
| **Purge / embargo** | A no-man's-land between two fields | Rows dropped around a split boundary so overlapping windows cannot leak | 14 |
| **Baseline** | The bar you have to clear before anyone looks at you | The simplest honest predictor; complexity must beat it by more than the noise | 12 |
| **Point vs event metric** | Grading each minute of a fire alarm vs whether each fire was noticed | Per-sample scores vs per-incident detection, delay and false alarms | 16 |
| **Cluster bootstrap** | Re-drawing whole classrooms, not single pupils | Resampling the independent unit so intervals are not falsely narrow | 17 |
| **Nested validation** | A referee who did not help pick the team | An outer loop that estimates the whole selection procedure | 15 |
| **Causal feature** | Driving using only the mirrors and the road ahead you have already passed | A feature at time *t* uses nothing after *t* | 11 |
| **Training/serving skew** | Rehearsing on a different stage from the performance | The served model computes inputs differently from the evaluated one | 25 |
| **Artifact bundle** | A sealed parcel with its packing list | Model parameters plus everything needed to trust and reload them | 26 |
| **Idempotent** | Pressing a lift button twice still calls one lift | Repeating an operation has the same effect as doing it once | 25, 35 |
| **Container image** | A frozen lunchbox; the container is the meal being eaten | A layered filesystem plus a start command; a container is a running instance | 31 |
| **Lockfile** | A recipe with brand names and quantities | Exact versions (and hashes) of every dependency | 32 |
| **CI** | A gate that checks every delivery | Automated checks on every push, before anything merges | 33 |
| **p95 latency** | The wait 1 in 20 customers exceeds | 95th percentile of response time; averages hide the tail | 34 |
| **Golden signals** | Pulse, temperature, breathing, blood pressure | Traffic, errors, latency, saturation of a service | 37 |
| **Drift** | The river moved; the boat may be fine | A change in the input distribution | 38 |
| **Degradation** | The boat is leaking | Measured loss of performance, which needs labels | 39 |
| **Canary / shadow** | A taster before the banquet / a dress rehearsal | Small live share vs scoring in parallel without serving | 40 |
| **Rollback** | The undo button that must already be tested | Pointing production back at the previous known-good version | 36, 40 |
| **Graceful degradation** | Stairs when the lift breaks, with a sign saying so | A simpler explicit fallback, flagged in the response, never silent | 41 |

## Course vocabulary

| Term | Meaning |
|---|---|
| **Session id** | `w<week>d<day>`; core sessions are notebooks 01-48 |
| **Guided / independent** | Passing supplied checks with the notebook's help / doing transfer work without hints or solutions |
| **Mutant** | A plausible wrong submission kept in `solutions/`; the checks must reject it |
| **Frozen manifest** | `v2.json`: the project's fixed split (7 test, 27 development experiments), used from Week 3 on |
| **SYNTHETIC** | Generated data; it supports conclusions about code and reasoning, not about real-world model quality |
