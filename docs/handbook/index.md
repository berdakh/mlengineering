---
title: Handbook
nav_order: 3
has_children: true
---

# Handbook: applied machine learning as reliable software

An original text written alongside the labs. Each section is meant to be sufficient to start
learning without another book; external sources are for verification and optional depth.

Every section has the same parts: overview, deeper explanation with examples, relevant equations,
practical decisions and tradeoffs, common failure modes, quick reference, sources and verification
status. Section ids (`H2.1`) are stable and are what lessons link to.


| Chapter | Sections |
|---|---|
| 1. Practical ML problem formulation | [H1.1 From stakeholder need to prediction target](ch01_problem_formulation/h1_1_stakeholder_need_to_prediction_target.md)<br>[H1.2 Units, labels, costs and constraints](ch01_problem_formulation/h1_2_units_labels_costs_constraints.md) |
| 2. Maintainable Python for ML | [H2.1 Project structure and environments](ch02_maintainable_python/h2_1_project_structure_environments.md)<br>[H2.2 Configuration, logging and reproducible runs](ch02_maintainable_python/h2_2_configuration_logging_runs.md)<br>[H2.3 Git workflow, linting and refactoring discipline](ch02_maintainable_python/h2_3_git_workflow_refactoring.md) |
| 3. SQL and data pipelines | [H3.1 Grain, joins, aggregation and NULLs](ch03_sql_data_pipelines/h3_1_grain_joins_aggregation_nulls.md)<br>[H3.2 Window functions and time-series SQL](ch03_sql_data_pipelines/h3_2_window_functions_timeseries_sql.md)<br>[H3.3 Ingestion and schemas](ch03_sql_data_pipelines/h3_3_ingestion_schemas.md)<br>[H3.4 Deterministic feature pipelines](ch03_sql_data_pipelines/h3_4_deterministic_feature_pipelines.md) |
| 4. Data quality and exploratory analysis | [H4.1 Quality checks as code; exploratory analysis that changes decisions](ch04_data_quality_eda/h4_1_quality_checks_and_eda.md) |
| 5. Classical ML and strong baselines | [H5.1 Trivial and linear baselines](ch05_classical_ml_baselines/h5_1_trivial_and_linear_baselines.md)<br>[H5.2 Metrics from decisions](ch05_classical_ml_baselines/h5_2_metrics_from_decisions.md)<br>[H5.3 Trees, ensembles and isolation forests](ch05_classical_ml_baselines/h5_3_trees_ensembles_iforest_pca.md)<br>[H5.4 Complexity versus evidence](ch05_classical_ml_baselines/h5_4_complexity_versus_evidence.md) |
| 6. Evaluation, leakage and uncertainty | [H6.1 Leakage: a taxonomy, detection probes and prevention by construction](ch06_evaluation_leakage_uncertainty/h6_1_leakage_taxonomy.md)<br>[H6.2 Thresholds, imbalance and calibration](ch06_evaluation_leakage_uncertainty/h6_2_thresholds_imbalance_calibration.md)<br>[H6.3 Group-aware and temporal validation](ch06_evaluation_leakage_uncertainty/h6_3_group_and_temporal_validation.md)<br>[H6.4 Selection and nested validation](ch06_evaluation_leakage_uncertainty/h6_4_selection_and_nested_validation.md)<br>[H6.5 Point-level versus event-level evaluation](ch06_evaluation_leakage_uncertainty/h6_5_point_vs_event_evaluation.md)<br>[H6.6 Bootstrap and paired comparisons](ch06_evaluation_leakage_uncertainty/h6_6_bootstrap_and_paired_comparisons.md)<br>[H6.7 Error analysis](ch06_evaluation_leakage_uncertainty/h6_7_error_analysis.md) |
| 7. Time-series and grouped-data modelling | [H7.1 Windowing and causality](ch07_timeseries_grouped_modeling/h7_1_windowing_and_causality.md)<br>[H7.2 Purging and embargo: buffers for windowed data](ch07_timeseries_grouped_modeling/h7_2_purging_and_embargo.md)<br>[H7.3 Event matching](ch07_timeseries_grouped_modeling/h7_3_event_matching.md)<br>[H7.4 Forecast-residual detection](ch07_timeseries_grouped_modeling/h7_4_forecast_residual_detection.md)<br>[H7.5 Multivariate detectors: PCA, Hotelling's T² and Q](ch07_timeseries_grouped_modeling/h7_5_multivariate_detectors.md)<br>[H7.6 Neural sequence models, fairly compared](ch07_timeseries_grouped_modeling/h7_6_neural_sequence_models.md) |
| 8. Reproducible experiments | [H8.1 Run registries and sweeps](ch08_reproducible_experiments/h8_1_run_registries_and_sweeps.md)<br>[H8.2 Seeds and variance](ch08_reproducible_experiments/h8_2_seeds_and_variance.md)<br>[H8.3 Clean-clone reproduction](ch08_reproducible_experiments/h8_3_clean_clone_reproduction.md) |
| 9. Testing ML systems | [H9.1 Unit testing ML code](ch09_testing_ml_systems/h9_1_unit_testing_ml_code.md)<br>[H9.2 API, integration and contract tests](ch09_testing_ml_systems/h9_2_api_integration_contract_tests.md) |
| 10. Batch and online inference | [H10.1 One pipeline for training and serving](ch10_batch_online_inference/h10_1_one_pipeline_for_training_and_serving.md)<br>[H10.2 Model artifacts and versioning](ch10_batch_online_inference/h10_2_artifacts_and_versioning.md)<br>[H10.3 Stateful online inference](ch10_batch_online_inference/h10_3_stateful_online_inference.md)<br>[H10.4 Latency and throughput](ch10_batch_online_inference/h10_4_latency_and_throughput.md) |
| 11. FastAPI and input validation | [H11.1 HTTP for ML engineers](ch11_fastapi_input_validation/h11_1_http_for_ml_engineers.md)<br>[H11.2 Schemas and validation](ch11_fastapi_input_validation/h11_2_schemas_and_validation.md)<br>[H11.3 Lifecycle and concurrency in a prediction service](ch11_fastapi_input_validation/h11_3_lifecycle_and_concurrency.md) |
| 12. Docker and reproducible environments | [H12.1 Images, layers and Dockerfiles](ch12_docker_reproducible_environments/h12_1_images_layers_dockerfiles.md)<br>[H12.2 Pinning, multi-stage builds and smoke tests](ch12_docker_reproducible_environments/h12_2_pinning_multistage_smoke_tests.md) |
| 13. One cloud deployment path | [H13.1 Identity, credentials and cost](ch13_cloud_deployment/h13_1_identity_credentials_cost.md)<br>[H13.2 Registry and a container service on AWS](ch13_cloud_deployment/h13_2_registry_and_container_service_on_aws.md) |
| 14. CI/CD fundamentals | [H14.1 Continuous integration](ch14_cicd/h14_1_continuous_integration.md)<br>[H14.2 Delivery, promotion and rollback](ch14_cicd/h14_2_delivery_promotion_rollback.md) |
| 15. Logging, monitoring and model updates | [H15.1 Service logs and metrics](ch15_logging_monitoring_updates/h15_1_service_logs_and_metrics.md)<br>[H15.2 Operational debugging](ch15_logging_monitoring_updates/h15_2_operational_debugging.md)<br>[H15.3 Input monitoring and drift statistics](ch15_logging_monitoring_updates/h15_3_input_monitoring_drift.md)<br>[H15.4 Drift versus degradation, delayed labels](ch15_logging_monitoring_updates/h15_4_drift_vs_degradation_delayed_labels.md)<br>[H15.5 Updates and rollback](ch15_logging_monitoring_updates/h15_5_updates_and_rollback.md)<br>[H15.6 Reliability patterns for ML services](ch15_logging_monitoring_updates/h15_6_reliability_patterns.md) |
| 16. ML system design and technical communication | [H16.1 Decision memos](ch16_system_design_communication/h16_1_decision_memos.md)<br>[H16.2 Reports and limitations](ch16_system_design_communication/h16_2_reports_and_limitations.md)<br>[H16.3 System design structure](ch16_system_design_communication/h16_3_system_design_structure.md)<br>[H16.4 Interview problem patterns](ch16_system_design_communication/h16_4_interview_problem_patterns.md) |

All 55 sections are written. Each ends with its sources and verification status; most were
checked against official documentation sources, and anything written from memory is labelled there.

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
