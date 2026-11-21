# Handbook: applied machine learning as reliable software

An original text written alongside the labs. Each section is meant to be sufficient to start
learning without another book; external sources are for verification and optional depth.

Every section has the same parts: overview, deeper explanation with examples, relevant equations,
practical decisions and tradeoffs, common failure modes, quick reference, sources and verification
status. Section ids (`H2.1`) are stable and are what lessons link to.

Status values: Planned, Draft, Reviewed, Execution verified (defined in `docs/AUTHORING.md`).

| Chapter | Sections | Status |
|---|---|---|
| 1. Practical ML problem formulation | H1.1 From stakeholder need to prediction target - H1.2 Units, labels, costs and constraints | Planned (w2d4) |
| 2. Maintainable Python for ML | **[H2.1 Project structure, environments, packaging](ch02_maintainable_python/h2_1_project_structure_environments.md)** - **[H2.2 Configuration, logging, reproducible runs](ch02_maintainable_python/h2_2_configuration_logging_runs.md)** - H2.3 Git workflow, linting and refactoring discipline | H2.1, H2.2 written (see STATUS.md); H2.3 planned (w1d6) |
| 3. SQL and data pipelines | H3.1 Grain, joins, aggregation, NULLs - H3.2 Window functions and time-series SQL - H3.3 Ingestion and schemas - H3.4 Deterministic feature pipelines | Planned (Week 2) |
| 4. Data quality and exploratory analysis | H4.1 Quality checks as code; exploratory analysis that changes decisions | Planned (w2d3) |
| 5. Classical ML and strong baselines | H5.1 Trivial and linear baselines - H5.2 Metrics from decisions - H5.3 Trees, ensembles, isolation forest, PCA detectors - H5.4 Complexity versus evidence | Planned (w2d6, Week 4) |
| 6. Evaluation, leakage and uncertainty | H6.1 Leakage taxonomy - H6.2 Thresholds, imbalance, calibration - H6.3 Group and temporal validation - H6.4 Selection and nested validation - H6.5 Point versus event evaluation - H6.6 Bootstrap and paired comparisons - H6.7 Error analysis | Planned (Week 3) |
| 7. Time-series and grouped-data modelling | H7.1 Windowing and causality - H7.2 Purging and embargo - H7.3 Event matching - H7.4 Forecast-residual detection - H7.5 Multivariate detectors - H7.6 Neural sequence models, fairly compared | Planned (Weeks 2-4) |
| 8. Reproducible experiments | H8.1 Run registries and sweeps - H8.2 Seeds and variance - H8.3 Clean-clone reproduction | Planned (Week 4, w8d1) |
| 9. Testing ML systems | **[H9.1 Unit-testing ML code](ch09_testing_ml_systems/h9_1_unit_testing_ml_code.md)** - H9.2 API, integration and contract tests | H9.1 written (see STATUS.md); H9.2 planned (w5d5) |
| 10. Batch and online inference | H10.1 One pipeline for training and serving - H10.2 Artifacts and versioning - H10.3 Stateful online inference - H10.4 Latency and throughput | Planned (Week 5, w6d4) |
| 11. FastAPI and input validation | H11.1 HTTP for ML engineers - H11.2 Schemas and validation - H11.3 Lifecycle and concurrency | Planned (Week 5) |
| 12. Docker and reproducible environments | H12.1 Images, layers, Dockerfiles - H12.2 Pinning, multi-stage builds, smoke tests | Planned (Week 6) |
| 13. One cloud deployment path | H13.1 Identity, credentials, cost - H13.2 Registry and a container service on AWS | Planned (w6d5) |
| 14. CI/CD fundamentals | H14.1 Continuous integration - H14.2 Delivery, promotion, rollback | Planned (Week 6) |
| 15. Logging, monitoring and model updates | H15.1 Service logs and metrics - H15.2 Operational debugging - H15.3 Input monitoring and drift statistics - H15.4 Drift versus degradation, delayed labels - H15.5 Updates and rollback - H15.6 Reliability patterns | Planned (Weeks 6-7) |
| 16. ML system design and technical communication | H16.1 Decision memos - H16.2 Reports and limitations - H16.3 System design structure - H16.4 Interview problem patterns | Planned (w4d5, Week 8) |

## Bridges from what you know

A recurring device in this handbook is to restate a familiar EEG/iEEG idea in another domain, and to
say where the analogy breaks.

| You already know | Same structure elsewhere | Where the analogy breaks |
|---|---|---|
| Subject-wise splits; cross-patient generalisation | Machine-, customer-, store- or site-wise splits | Business groups are often open-ended and changing; new groups appear daily |
| Line length, band power, RMS on EEG windows | Vibration and current features in equipment monitoring | Sampling rates, sensor bandwidth and physics-based fault frequencies differ |
| HFO or seizure event detection scored by event overlap and latency | Fault-event detection scored by event recall and detection delay | Industrial events are rarer and labels come from maintenance logs with delays |
| Non-stationarity across sessions, electrode drift | Sensor recalibration, seasonal demand, product changes | Drift may be intentional (a price change) and documented outside the data |
| Artefact rejection | Data-quality rules and input validation at the API boundary | Rejection must be automatic, logged and reversible in production |
| Real-time BCI loop latency | Online inference latency budgets (p95/p99) | Budgets are contractual; failures need fallbacks rather than a restarted session |
