# Applied ML Engineering — an eight-week, hands-on program

**Eight weeks · 48 notebooks · everything runs on your own laptop or in Colab.**

Take a model from a research script to a reliable service: package it, test it, frame the problem
properly, evaluate it without fooling yourself, serve it through an API, containerise and deploy it,
then monitor it, update it and explain it. One real time-series project runs through all eight weeks.

📖 **[Read the full course site →](https://berdakh.github.io/mlengineering-/)**

---

<img src="docs/assets/diagrams/roadmap.svg" alt="The eight-week roadmap: software foundations, data, evaluation, models, serving, deployment, operations, and finishing" width="100%">

## What you will be able to do

By the end of eight weeks, with evidence you produced yourself:

1. **Translate** a practical problem into an ML task: unit of prediction, labels, costs, constraints.
2. **Build a reproducible data pipeline** with schema and quality checks that fail loudly.
3. **Establish meaningful baselines** and choose metrics from the decision being supported.
4. **Train, compare and analyse models correctly**: no leakage, honest validation, intervals, error analysis.
5. **Package preprocessing and inference** once, and prove training/serving parity.
6. **Write useful tests** and maintainable code: packages, configuration, logging, CI.
7. **Expose predictions through a validated API** with FastAPI.
8. **Containerise and deploy** a small service, behind an explicit cost gate.
9. **Measure latency, failures and model behaviour**, and tell input drift from real degradation.
10. **Explain decisions, limitations and tradeoffs** in a report, a walkthrough and system-design interviews.

## Who it is for

You train models already (PyTorch, scikit-learn, time series) and want to deliver them as software.
You need comfortable Python and a terminal. You do **not** need a GPU or any paid service.

| You have | You can do |
|---|---|
| Any laptop with Python 3.11+ | Everything except the container sessions |
| The same, plus Docker Engine | Everything except the optional cloud step |
| No install at all | Read everything on the site; run notebooks in free Google Colab |
| An AWS account (optional) | The gated deployment step in notebook 35. Never required |

---

## Quick start

```bash
git clone https://github.com/berdakh/mlengineering-.git
cd mlengineering-

python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-lock.txt -r requirements-dev.txt

python scripts/check_env.py           # what can this machine run?
python project/get_skab.py            # the project data, about 4 MB (needed from notebook 06)
jupyter lab notebooks/01_diagnostic_a.ipynb
```

**No install at all?** Click any *Colab* badge below: the first cell clones the repository and installs
everything. See [docs/guides/colab.md](docs/guides/colab.md). Full setup, including Pop!_OS notes:
**[docs/guides/setup.md](docs/guides/setup.md)**.

---

## The notebooks

**Every notebook is readable on the [course site](https://berdakh.github.io/mlengineering-/notebooks/)
and opens in Colab with one click.** Each core day is about **2 hours** (plus an optional hour) and follows
the same eight parts: purpose · concepts · worked example · guided lab with automated checks · independent
challenge · progressive hints · assessment · reflection. You edit files in `labs/<session>/`; the notebook
runs the checks.

| # | Notebook | You learn to | Colab |
|---|---|---|---|
| **Week 1 — From research code to software** ||||
| 01 | [Diagnostic A: Python, SQL, data cleaning](notebooks/01_diagnostic_a.ipynb) | Produce time-boxed, unassisted evidence of current skill in Python refactoring/debugging, SQL joins and aggregation,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/01_diagnostic_a.ipynb) |
| 02 | [Diagnostic B: baselines, leakage, testing/API, explaining a decision](notebooks/02_diagnostic_b.ipynb) | Produce time-boxed, unassisted evidence in baseline modelling on an unfamiliar business table, leakage detection,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/02_diagnostic_b.ipynb) |
| 03 | [From script to installable package: project structure and environments](notebooks/03_package_structure.ipynb) | Turn a notebook-export script into a src-layout package with pyproject.toml, an isolated environment, an editable… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/03_package_structure.ipynb) |
| 04 | [Configuration, logging and reproducible runs](notebooks/04_config_logging.ipynb) | Make a training run reproducible and inspectable: typed validated config with overrides, logging configured once,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/04_config_logging.ipynb) |
| 05 | [Testing ML code with pytest: what a unit test can and cannot tell you](notebooks/05_testing_ml_code.ipynb) | Write a pytest suite that catches realistic defects in signal-feature and splitting code, and separate deterministic… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/05_testing_ml_code.ipynb) |
| 06 | [Independent refactor: a real exploratory notebook becomes the project skeleton](notebooks/06_notebook_to_package.ipynb) | Without step-by-step guidance, refactor an exploratory notebook on the project dataset into the `flowguard` package… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/06_notebook_to_package.ipynb) |
| | *Day 7: review, retrieval practice and interview set 1* — [week 1 page](docs/weeks/week-1.md#day-7--review-and-catch-up) | | |
| **Week 2 — Data: SQL, pandas, quality, features, baselines** ||||
| 07 | [SQL I: grain, joins, aggregation and NULL semantics](notebooks/07_sql_joins_grain.ipynb) | Write correct multi-table queries by reasoning about table grain first | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/07_sql_joins_grain.ipynb) |
| 08 | [SQL II: CTEs, window functions and time-series queries](notebooks/08_sql_windows_timeseries.ipynb) | Use window functions for ranking, running statistics, gaps-and-islands and as-of joins on event and sensor tables | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/08_sql_windows_timeseries.ipynb) |
| 09 | [pandas ingestion, schemas and data-quality checks (project data arrives)](notebooks/09_data_quality_ingestion.ipynb) | Ingest the project dataset through a documented, re-runnable step with explicit schema and quality checks expressed… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/09_data_quality_ingestion.ipynb) |
| 10 | [Problem framing and versioned split definitions](notebooks/10_problem_framing_splits.ipynb) | Translate the stakeholder problem into an ML task: unit of prediction, label definition (point vs event), costs of… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/10_problem_framing_splits.ipynb) |
| 11 | [Reproducible feature generation without look-ahead](notebooks/11_feature_pipeline.ipynb) | Build causal rolling-window features and train-only statistics as a deterministic, cached, tested pipeline step | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/11_feature_pipeline.ipynb) |
| 12 | [Strong simple baselines and metrics that match the decision](notebooks/12_baselines_metrics.ipynb) | Establish trivial and classical baselines and choose metrics from the decision (imbalance, PR vs ROC, thresholds,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/12_baselines_metrics.ipynb) |
| | *Day 7: review, retrieval practice and interview set 2* — [week 2 page](docs/weeks/week-2.md#day-7--review-and-catch-up) | | |
| **Week 3 — Evaluation you can defend** ||||
| 13 | [Leakage: a taxonomy and prevention by construction](notebooks/13_leakage.ipynb) | Classify and remove target, preprocessing, temporal, group and selection leakage | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/13_leakage.ipynb) |
| 14 | [Group-aware and temporal validation](notebooks/14_group_temporal_validation.ipynb) | Design validation that matches deployment: grouped, temporal, and combined (experiment x time) schemes with… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/14_group_temporal_validation.ipynb) |
| 15 | [Hyperparameter and threshold selection without fooling yourself](notebooks/15_hyperparameter_selection.ipynb) | Select hyperparameters and decision thresholds using only training/validation data | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/15_hyperparameter_selection.ipynb) |
| 16 | [Point-level versus event-level evaluation for detection](notebooks/16_point_vs_event_evaluation.ipynb) | Implement and interpret point-wise metrics, event matching, detection delay and false alarms per hour | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/16_point_vs_event_evaluation.ipynb) |
| 17 | [Uncertainty: cluster bootstrap, paired comparisons, small-n honesty](notebooks/17_uncertainty.ipynb) | Attach defensible intervals to metrics when the independent unit is the experiment, not the sample | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/17_uncertainty.ipynb) |
| 18 | [Error analysis and timed transfer exercise](notebooks/18_error_analysis_transfer.ipynb) | Turn errors into a ranked failure taxonomy with slices | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/18_error_analysis_transfer.ipynb) |
| | *Day 7: review, retrieval practice and interview set 3* — [week 3 page](docs/weeks/week-3.md#day-7--review-and-catch-up) | | |
| **Week 4 — Time-series models and choosing on evidence** ||||
| 19 | [Time-series fundamentals and forecast-residual detectors](notebooks/19_timeseries_fundamentals.ipynb) | Reason about autocorrelation, non-stationarity and windowing | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/19_timeseries_fundamentals.ipynb) |
| 20 | [Classical detectors: PCA/T2-Q, isolation forest, boosted trees on window features](notebooks/20_classical_detectors.ipynb) | Fit methods to the label structure (semi-supervised vs supervised framing) and compare them under one protocol and… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/20_classical_detectors.ipynb) |
| 21 | [A neural comparison, where it is justified](notebooks/21_neural_comparison.ipynb) | Train a small 1D-CNN or LSTM autoencoder (PyTorch, CPU) with a fair tuning budget and multiple seeds | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/21_neural_comparison.ipynb) |
| 22 | [Experiment tracking and reproducibility at the experiment level](notebooks/22_experiment_tracking.ipynb) | Manage many runs: sweep configs, registry of runs, aggregate results table, reproduce any row from its run id | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/22_experiment_tracking.ipynb) |
| 23 | [Choosing complexity on evidence](notebooks/23_model_choice.ipynb) | Decide between candidates using effect size versus uncertainty, error costs, latency, size and maintenance burden | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/23_model_choice.ipynb) |
| 24 | [Project milestone 1: evaluation report](notebooks/24_project_milestone_1.ipynb) | Assemble the model comparison and error analysis into a reproducible report generated by commands | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/24_project_milestone_1.ipynb) |
| | *Day 7: review, retrieval practice and interview set 4* — [week 4 page](docs/weeks/week-4.md#day-7--review-and-catch-up) | | |
| **Week 5 — Inference, artifacts and a prediction API** ||||
| 25 | [Research experimentation versus production inference](notebooks/25_inference_pipeline.ipynb) | Package preprocessing and model as one inference object used identically in training evaluation and serving | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/25_inference_pipeline.ipynb) |
| 26 | [Model artifacts, metadata and versioning](notebooks/26_artifacts_versioning.ipynb) | Serialise models with the metadata needed to trust and reload them (schema, feature list, versions, data and code… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/26_artifacts_versioning.ipynb) |
| 27 | [Online inference on streams: state, warm-up and parity](notebooks/27_online_inference.ipynb) | Implement stateful windowed scoring for one-sample-at-a-time input and prove parity with batch scoring | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/27_online_inference.ipynb) |
| 28 | [FastAPI I: endpoints, schemas and input validation](notebooks/28_fastapi_validation.ipynb) | Expose predictions through a typed HTTP API: request/response models, validation errors versus server errors, health… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/28_fastapi_validation.ipynb) |
| 29 | [FastAPI II: API tests, integration tests and model lifecycle](notebooks/29_api_testing.ipynb) | Test the service at the HTTP boundary (happy path, invalid input, model missing), manage model loading at startup,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/29_api_testing.ipynb) |
| 30 | [Project milestone 2: packaged inference + API](notebooks/30_project_milestone_2.ipynb) | Integrate artifact, inference pipeline and API in the project with tests and usage documentation | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/30_project_milestone_2.ipynb) |
| | *Day 7: review, retrieval practice and interview set 5* — [week 5 page](docs/weeks/week-5.md#day-7--review-and-catch-up) | | |
| **Week 6 — Containers, CI/CD and one cloud deployment** ||||
| 31 | [Docker I: images, layers and a correct Dockerfile](notebooks/31_docker_basics.ipynb) | Explain what an image and container are | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/31_docker_basics.ipynb) |
| 32 | [Docker II: pinned dependencies, multi-stage builds, smoke tests](notebooks/32_docker_reproducibility.ipynb) | Make the environment reproducible (lockfile, pinned base image digest), reduce image size, and smoke-test the container | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/32_docker_reproducibility.ipynb) |
| 33 | [Continuous integration with GitHub Actions](notebooks/33_ci.ipynb) | Automate lint, tests and image build on every push | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/33_ci.ipynb) |
| 34 | [Latency, throughput and resource use](notebooks/34_latency_resources.ipynb) | Measure p50/p95/p99 latency and memory under load, find the bottleneck, and tune workers/batching against a stated… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/34_latency_resources.ipynb) |
| 35 | [One small cloud deployment on AWS (authorisation-gated)](notebooks/35_cloud_deployment.ipynb) | Understand IAM, credentials, registries and cost | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/35_cloud_deployment.ipynb) |
| 36 | [Delivery and operational debugging; project milestone 3](notebooks/36_cd_ops_debugging.ipynb) | Promote an image by tag, configure through environment, read logs to diagnose seeded failures, and roll back | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/36_cd_ops_debugging.ipynb) |
| | *Day 7: review, retrieval practice and interview set 6* — [week 6 page](docs/weeks/week-6.md#day-7--review-and-catch-up) | | |
| **Week 7 — Operating a model** ||||
| 37 | [Structured logging and service metrics](notebooks/37_service_logging_metrics.ipynb) | Emit structured request and prediction logs with correlation ids | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/37_service_logging_metrics.ipynb) |
| 38 | [Input monitoring and drift statistics](notebooks/38_input_monitoring_drift.ipynb) | Detect schema violations, range and missingness changes and distribution shift (PSI, KS, Wasserstein) with windows… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/38_input_monitoring_drift.ipynb) |
| 39 | [Drift is not degradation: delayed labels and measured performance](notebooks/39_drift_vs_degradation.ipynb) | Separate input change from measured performance loss | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/39_drift_vs_degradation.ipynb) |
| 40 | [Model updates: retraining triggers, shadow and canary, rollback](notebooks/40_model_updates_rollback.ipynb) | Define when and how a model is replaced: triggers, offline gate, shadow/canary comparison, versioned rollback | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/40_model_updates_rollback.ipynb) |
| 41 | [Reliability and failure handling](notebooks/41_reliability.ipynb) | Handle bad input, timeouts, missing models and dependency failures deliberately: guards, fallbacks, degradation,… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/41_reliability.ipynb) |
| 42 | [Project milestone 4: monitoring demonstration and runbook](notebooks/42_project_milestone_4.ipynb) | Demonstrate monitoring on a replay of held-out experiments and document operating procedures | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/42_project_milestone_4.ipynb) |
| | *Day 7: review, retrieval practice and interview set 7* — [week 7 page](docs/weeks/week-7.md#day-7--review-and-catch-up) | | |
| **Week 8 — Finish, document, explain** ||||
| 43 | [Project completion audit: reproduce from a clean clone](notebooks/43_project_completion.ipynb) | Audit the project against the deliverables checklist and reproduce every headline number from a fresh clone | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/43_project_completion.ipynb) |
| 44 | [Technical report and model limitations](notebooks/44_report_limitations.ipynb) | Write a short technical report and a limitations section that a sceptical reviewer would accept | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/44_report_limitations.ipynb) |
| 45 | [ML system design](notebooks/45_system_design.ipynb) | Apply a repeatable structure (requirements, data, labels, evaluation, serving, monitoring, iteration) to two timed… | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/45_system_design.ipynb) |
| 46 | [Coding and SQL interviews, timed](notebooks/46_coding_interviews.ipynb) | Solve Python data-structure and SQL problems under time pressure while explaining aloud | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/46_coding_interviews.ipynb) |
| 47 | [Explaining the project and defending tradeoffs](notebooks/47_project_explanation.ipynb) | Deliver 5-minute and 20-minute walkthroughs and answer adversarial questions on evaluation, limitations and alternatives | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/47_project_explanation.ipynb) |
| 48 | [Final independent assessment](notebooks/48_final_assessment.ipynb) | Complete a parallel form of the diagnostic and the final transfer task unassisted, for comparison with Week 1 evidence | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/berdakh/mlengineering-/blob/main/notebooks/48_final_assessment.ipynb) |
| | *Day 7: review, retrieval practice and interview set 8* — [week 8 page](docs/weeks/week-8.md#day-7--review-and-catch-up) | | |

Notebooks **01-02 are a diagnostic**: time-boxed and unassisted. Their results decide which Week 1-3 sessions
you can compress. Notebook **48 is the final assessment**, a parallel form of the diagnostic for comparison.

## The handbook — background reading

The notebooks teach you to build. The **[handbook](docs/handbook/index.md)** explains what you are building on:
55 original sections with equations, decisions and tradeoffs, failure modes, a quick reference and sources.

| Chapter | |
|---|---|
| [1. Practical ML problem formulation](docs/handbook/ch01_problem_formulation/index.md) | 2 sections |
| [2. Maintainable Python for ML](docs/handbook/ch02_maintainable_python/index.md) | 3 sections |
| [3. SQL and data pipelines](docs/handbook/ch03_sql_data_pipelines/index.md) | 4 sections |
| [4. Data quality and exploratory analysis](docs/handbook/ch04_data_quality_eda/index.md) | 1 section |
| [5. Classical ML and strong baselines](docs/handbook/ch05_classical_ml_baselines/index.md) | 4 sections |
| [6. Evaluation, leakage and uncertainty](docs/handbook/ch06_evaluation_leakage_uncertainty/index.md) | 7 sections |
| [7. Time-series and grouped-data modelling](docs/handbook/ch07_timeseries_grouped_modeling/index.md) | 6 sections |
| [8. Reproducible experiments](docs/handbook/ch08_reproducible_experiments/index.md) | 3 sections |
| [9. Testing ML systems](docs/handbook/ch09_testing_ml_systems/index.md) | 2 sections |
| [10. Batch and online inference](docs/handbook/ch10_batch_online_inference/index.md) | 4 sections |
| [11. FastAPI and input validation](docs/handbook/ch11_fastapi_input_validation/index.md) | 3 sections |
| [12. Docker and reproducible environments](docs/handbook/ch12_docker_reproducible_environments/index.md) | 2 sections |
| [13. One cloud deployment path](docs/handbook/ch13_cloud_deployment/index.md) | 2 sections |
| [14. CI/CD fundamentals](docs/handbook/ch14_cicd/index.md) | 2 sections |
| [15. Logging, monitoring and model updates](docs/handbook/ch15_logging_monitoring_updates/index.md) | 6 sections |
| [16. ML system design and technical communication](docs/handbook/ch16_system_design_communication/index.md) | 4 sections |

## Guides

| Guide | About |
|---|---|
| [Before you start](docs/guides/before-you-start.md) | What you need, what is assumed, the first session |
| [Setup](docs/guides/setup.md) · [Colab](docs/guides/colab.md) | Local install or no install |
| [Cheat sheet](docs/guides/cheatsheet.md) · [Troubleshooting](docs/guides/troubleshooting.md) · [Glossary](docs/guides/glossary.md) | Daily commands, fixes, vocabulary |
| [The portfolio project](docs/guides/project.md) | `flowguard` on the SKAB testbed: provenance, findings, deliverables |
| [Interview practice](docs/guides/interview-practice.md) | Seven timed sets with rubrics |
| [Full schedule](docs/guides/schedule.md) · [Program design](docs/guides/program-design.md) | All 56 sessions; the reasoning behind the plan |
| [Status and verification](docs/guides/status.md) | What was executed, what was not, known limitations |

## Solutions

Reference solutions, model answers and the wrong submissions each check is verified to reject:
**[solutions/](solutions/README.md)** ([exercises](solutions/exercises.md) · [checkpoints](solutions/checkpoints.md)).
Open them after a real attempt; the diagnostic and final assessment only tell you something if you do.

## Tracking progress

```bash
python wb.py next                  # what to study next
python wb.py check w3d4            # grade your lab (add --challenge for the challenge)
python wb.py mark w3d4 guided      # flags: reading | guided | independent | review
streamlit run app/study_app.py     # optional study app (pip install -r requirements-app.txt)
```

Passing the supplied checks is *guided practice*. Mark *independent* only for work done without hints or solutions.

## Repository layout

| Path | What it is |
|---|---|
| `notebooks/` | The 48 notebooks (built from `notebook_src/`; edit the sources, then `make notebooks`) |
| `labs/<session>/` | Lab and challenge starters, worked-example scripts, data, checks |
| `diagnostic/` | The diagnostic sections used by notebooks 01-02 |
| `docs/` | The course site: weeks, handbook, guides, rendered notebooks |
| `solutions/` | Reference solutions and answers |
| `interview/` | Interview prompt sets and their test harnesses |
| `src/mlcourse/` | Small helpers the notebooks import (checks, progress, data) |
| `project/`, `data/` | Project data download and synthetic lab data |
| `progress/` | Your progress flags, notes and skills ledger |
| `tools/`, `scripts/`, `app/`, `wb.py` | Build and check tools, environment check, study app, command-line helper |

## Licence

Code is MIT licensed; prose is CC BY 4.0 (see [LICENSE](LICENSE)). The SKAB dataset is GPL-3.0 and is
downloaded from its source, never redistributed here. Educational material: no claim about any real plant.
