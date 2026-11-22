"""Single source of truth for the unit list. Regenerates course.json and roadmap/SCHEDULE.md.

    python tools/build_course.py

Edit UNITS below (status, path, wording), then rerun. Status values are defined in
docs/AUTHORING.md: Planned | Draft | Reviewed | Execution verified.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WEEK_THEMES = {
    1: "From research code to software",
    2: "Data: SQL, pandas, quality, features, baselines",
    3: "Evaluation you can defend: leakage, validation, uncertainty",
    4: "Time-series modelling and evidence-based model choice",
    5: "Inference pipelines, artifacts and a prediction API",
    6: "Containers, CI/CD and one cloud deployment",
    7: "Operating a model: logging, monitoring, updates, reliability",
    8: "Finish, document, explain",
}

# (id, title, objective, deliverable, prerequisites, handbook refs)
U = []


def unit(uid, title, objective, deliverable, prereq, handbook, path=None, status="Planned", has_checks=False):
    week, day = int(uid[1]), int(uid[3])
    U.append(dict(id=uid, week=week, day=day, title=title, objective=objective, deliverable=deliverable,
                  prerequisites=prereq, handbook=handbook, path=path, status=status, has_checks=has_checks))


REVIEW = ("Retrieve, do not re-read: answer the week's retrieval questions from memory, redo one failed "
          "check or challenge unassisted, complete the mixed interview set, update progress flags.")

# ---------------------------------------------------------------- Week 1
unit("w1d1_diagnostic_a", "Diagnostic A: Python, SQL, data cleaning",
     "Produce time-boxed, unassisted evidence of current skill in Python refactoring/debugging, SQL joins and aggregation, and pandas data cleaning.",
     "Completed labs for a1/a2/a3 plus the Session A part of diagnostic/SUBMISSION.md.",
     "Working Python >= 3.11 environment (README, 'Set up').", "-", path="diagnostic", status="Execution verified")
unit("w1d2_diagnostic_b", "Diagnostic B: baselines, leakage, testing/API, explaining a decision",
     "Produce time-boxed, unassisted evidence in baseline modelling on an unfamiliar business table, leakage detection, test writing, API concepts and written justification.",
     "Completed labs for b1/b2/b3, the written b4 answer, and the finished diagnostic/SUBMISSION.md.",
     "w1d1.", "-", path="diagnostic", status="Execution verified")
unit("w1d3_package_structure", "From script to installable package: project structure and environments",
     "Turn a notebook-export script into a src-layout package with pyproject.toml, an isolated environment, an editable install and a console entry point, proving behaviour is preserved.",
     "Installable `pumpwatch` package + refactoring log with before/after metrics.",
     "Diagnostic submitted (or explicitly deferred).", "H2.1", path="lessons/w1d3_package_structure", status="Execution verified", has_checks=True)
unit("w1d4_config_logging", "Configuration, logging and reproducible runs",
     "Make a training run reproducible and inspectable: typed validated config with overrides, logging configured once, explicit seeds, and a run directory with config snapshot, metrics and provenance.",
     "`pumpwatch` v0.2 producing self-describing run directories; two identical runs shown to match.",
     "w1d3.", "H2.2", path="lessons/w1d4_config_logging", status="Execution verified", has_checks=True)
unit("w1d5_testing_ml_code", "Testing ML code with pytest: what a unit test can and cannot tell you",
     "Write a pytest suite that catches realistic defects in signal-feature and splitting code, and separate deterministic unit tests from statistical performance checks.",
     "A test suite that kills the seeded bugs (mutation-graded) and a one-paragraph note on what it does not establish.",
     "w1d3 (w1d4 helpful).", "H9.1", path="lessons/w1d5_testing_ml_code", status="Execution verified", has_checks=True)
unit("w1d6_notebook_to_package", "Independent refactor: a real exploratory notebook becomes the project skeleton",
     "Without step-by-step guidance, refactor an exploratory notebook on the project dataset into the `flowguard` package skeleton using small reviewed Git commits (branch, commit hygiene, .gitignore, lint).",
     "Project repository skeleton: package, config, tests, README stub, clean commit history.",
     "w1d3-w1d5.", "H2.3 (Git workflow, linting), H2.1, H9.1", path="lessons/w1d6_notebook_to_package", status="Execution verified", has_checks=True)
unit("w1d7_review", "Review and catch-up (light)", REVIEW,
     "Week 1 retrieval sheet answered; interview set 1 (Python + project structure).", "Week 1 units.", "-", path="lessons/w1d7_review", status="Execution verified")

# ---------------------------------------------------------------- Week 2
unit("w2d1_sql_joins_grain", "SQL I: grain, joins, aggregation and NULL semantics",
     "Write correct multi-table queries by reasoning about table grain first; recognise fan-out, NULL and anti-join traps.",
     "Solved query set with a stated grain for every result; fan-out bug report on a broken query.",
     "Diagnostic a2 reviewed.", "H3.1", path="lessons/w2d1_sql_joins_grain", status="Execution verified", has_checks=True)
unit("w2d2_sql_windows_timeseries", "SQL II: CTEs, window functions and time-series queries",
     "Use window functions for ranking, running statistics, gaps-and-islands and as-of joins on event and sensor tables; reproduce each result in pandas.",
     "Query set + pandas equivalence tests; a point-in-time-correct feature query.",
     "w2d1.", "H3.2", path="lessons/w2d2_sql_windows_timeseries", status="Execution verified", has_checks=True)
unit("w2d3_data_quality_ingestion", "pandas ingestion, schemas and data-quality checks (project data arrives)",
     "Ingest the project dataset through a documented, re-runnable step with explicit schema and quality checks expressed as code that fails loudly.",
     "`flowguard ingest` command, data dictionary, data-quality report, provenance record (source, licence, hashes).",
     "w1d6; diagnostic a3 reviewed.", "H3.3, H4.1", path="lessons/w2d3_data_quality_ingestion", status="Execution verified", has_checks=True)
unit("w2d4_problem_framing_splits", "Problem framing and versioned split definitions",
     "Translate the stakeholder problem into an ML task: unit of prediction, label definition (point vs event), costs of errors, constraints; freeze splits by experiment and time in a versioned manifest.",
     "Problem statement, label definition, `splits/v1.json` manifest with a leakage-safety test.",
     "w2d3.", "H1.1, H1.2, H6.1", path="lessons/w2d4_problem_framing_splits", status="Execution verified", has_checks=True)
unit("w2d5_feature_pipeline", "Reproducible feature generation without look-ahead",
     "Build causal rolling-window features and train-only statistics as a deterministic, cached, tested pipeline step.",
     "Feature pipeline with no-look-ahead tests and content-addressed outputs.",
     "w2d4, w1d5.", "H3.4, H7.1", path="lessons/w2d5_feature_pipeline", status="Execution verified", has_checks=True)
unit("w2d6_baselines_metrics", "Strong simple baselines and metrics that match the decision",
     "Establish trivial and classical baselines and choose metrics from the decision (imbalance, PR vs ROC, thresholds, calibration basics) on the project data and on an unfamiliar business table.",
     "Baseline table for the project (trivial, threshold, linear); transfer exercise part 1 baseline.",
     "w2d5; diagnostic b1 reviewed.", "H5.1, H5.2, H6.2", path="lessons/w2d6_baselines_metrics", status="Execution verified", has_checks=True)
unit("w2d7_review", "Review and catch-up (light)", REVIEW,
     "Week 2 retrieval sheet; interview set 2 (SQL + pandas, timed).", "Week 2 units.", "-", path="lessons/w2d7_review", status="Execution verified")

# ---------------------------------------------------------------- Week 3
unit("w3d1_leakage", "Leakage: a taxonomy and prevention by construction",
     "Classify and remove target, preprocessing, temporal, group and selection leakage; use pipelines so the correct thing is the default.",
     "Leak hunt report on a seeded dataset with corrected estimates and the mechanism of each leak.",
     "w2d6; diagnostic b2 reviewed.", "H6.1", path="lessons/w3d1_leakage", status="Execution verified", has_checks=True)
unit("w3d2_group_temporal_validation", "Group-aware and temporal validation",
     "Design validation that matches deployment: grouped, temporal, and combined (experiment x time) schemes with purging/embargo where windows overlap.",
     "Validation design memo + implementation for the project; comparison against a naive random split.",
     "w3d1.", "H6.3, H7.2", path="lessons/w3d2_group_temporal_validation", status="Execution verified", has_checks=True)
unit("w3d3_hyperparameter_selection", "Hyperparameter and threshold selection without fooling yourself",
     "Select hyperparameters and decision thresholds using only training/validation data; quantify selection optimism with nested validation.",
     "Tuned baseline with a nested estimate and a frozen-threshold test evaluation.",
     "w3d2.", "H6.4", path="lessons/w3d3_hyperparameter_selection", status="Execution verified", has_checks=True)
unit("w3d4_point_vs_event_evaluation", "Point-level versus event-level evaluation for detection",
     "Implement and interpret point-wise metrics, event matching, detection delay and false alarms per hour; explain when each misleads.",
     "Tested `flowguard.evaluation` module; point vs event results table with interpretation.",
     "w3d2 (your HFO event-evaluation experience transfers directly).", "H6.5, H7.3", path="lessons/w3d4_point_vs_event_evaluation", status="Execution verified", has_checks=True)
unit("w3d5_uncertainty", "Uncertainty: cluster bootstrap, paired comparisons, small-n honesty",
     "Attach defensible intervals to metrics when the independent unit is the experiment, not the sample; compare models with paired resampling.",
     "Confidence intervals and a paired comparison for the baselines, with a stated unit of resampling.",
     "w3d4.", "H6.6", path="lessons/w3d5_uncertainty", status="Execution verified", has_checks=True)
unit("w3d6_error_analysis_transfer", "Error analysis and timed transfer exercise",
     "Turn errors into a ranked failure taxonomy with slices; then run a complete leak-free evaluation on the unfamiliar business table, unassisted, in 90 minutes.",
     "Project error-analysis note; transfer exercise part 2 submission.",
     "w3d1-w3d5.", "H6.7", path="lessons/w3d6_error_analysis_transfer", status="Execution verified", has_checks=True)
unit("w3d7_review", "Review and catch-up (light)", REVIEW,
     "Week 3 retrieval sheet; interview set 3 (validation, leakage, ML fundamentals, spoken answers).", "Week 3 units.", "-", path="lessons/w3d7_review", status="Execution verified")

# ---------------------------------------------------------------- Week 4
unit("w4d1_timeseries_fundamentals", "Time-series fundamentals and forecast-residual detectors",
     "Reason about autocorrelation, non-stationarity and windowing; build naive, seasonal-naive and autoregressive forecasters and use their residuals as anomaly scores.",
     "Residual-based detector evaluated with the Week 3 protocol.",
     "Week 3.", "H7.1, H7.4", path="lessons/w4d1_timeseries_fundamentals")
unit("w4d2_classical_detectors", "Classical detectors: PCA/T2-Q, isolation forest, boosted trees on window features",
     "Fit methods to the label structure (semi-supervised vs supervised framing) and compare them under one protocol and compute budget.",
     "Comparison table with intervals; note on which framing the labels support.",
     "w4d1.", "H5.3, H7.5", path="lessons/w4d2_classical_detectors")
unit("w4d3_neural_comparison", "A neural comparison, where it is justified",
     "Train a small 1D-CNN or LSTM autoencoder (PyTorch, CPU) with a fair tuning budget and multiple seeds; report seed variance.",
     "Neural result with seed variance in the comparison table; GPU optional.",
     "w4d2; PyTorch (demonstrated in research).", "H7.6", path="lessons/w4d3_neural_comparison", status="Execution verified", has_checks=True)
unit("w4d4_experiment_tracking", "Experiment tracking and reproducibility at the experiment level",
     "Manage many runs: sweep configs, registry of runs, aggregate results table, reproduce any row from its run id.",
     "`flowguard sweep` + results table generated from run directories (MLflow as an optional extension).",
     "w1d4, w4d2.", "H8.1, H8.2", path="lessons/w4d4_experiment_tracking", status="Execution verified", has_checks=True)
unit("w4d5_model_choice", "Choosing complexity on evidence",
     "Decide between candidates using effect size versus uncertainty, error costs, latency, size and maintenance burden.",
     "One-page decision memo choosing the model to ship.",
     "w4d3, w4d4, w3d5.", "H5.4, H16.1", path="lessons/w4d5_model_choice")
unit("w4d6_project_milestone_1", "Project milestone 1: evaluation report",
     "Assemble the model comparison and error analysis into a reproducible report generated by commands.",
     "`make evaluate` regenerates the comparison report; submit for review.",
     "w4d5.", "-", path="lessons/w4d6_project_milestone_1")
unit("w4d7_review", "Review and catch-up (light)", REVIEW,
     "Week 4 retrieval sheet; interview set 4 (explain your evaluation in 5 minutes, recorded).", "Week 4 units.", "-", path="lessons/w4d7_review")

# ---------------------------------------------------------------- Week 5
unit("w5d1_inference_pipeline", "Research experimentation versus production inference",
     "Package preprocessing and model as one inference object used identically in training evaluation and serving; build a batch inference command.",
     "`flowguard predict-batch` with a training/serving parity test.",
     "w4d6.", "H10.1")
unit("w5d2_artifacts_versioning", "Model artifacts, metadata and versioning",
     "Serialise models with the metadata needed to trust and reload them (schema, feature list, versions, data and code hashes); understand pickle risks and alternatives.",
     "Versioned artifact bundle + load-time compatibility checks + model card draft.",
     "w5d1.", "H10.2")
unit("w5d3_online_inference", "Online inference on streams: state, warm-up and parity",
     "Implement stateful windowed scoring for one-sample-at-a-time input and prove parity with batch scoring.",
     "Streaming scorer with batch/online parity tests and documented warm-up behaviour.",
     "w5d1, w2d5.", "H10.3")
unit("w5d4_fastapi_validation", "FastAPI I: endpoints, schemas and input validation",
     "Expose predictions through a typed HTTP API: request/response models, validation errors versus server errors, health and readiness endpoints.",
     "`/predict`, `/healthz`, `/readyz` with pydantic schemas and documented error model.",
     "w5d2; diagnostic b3 reviewed.", "H11.1, H11.2")
unit("w5d5_api_testing", "FastAPI II: API tests, integration tests and model lifecycle",
     "Test the service at the HTTP boundary (happy path, invalid input, model missing), manage model loading at startup, reason about concurrency.",
     "API and integration test suite running without a network.",
     "w5d4, w1d5.", "H9.2, H11.3")
unit("w5d6_project_milestone_2", "Project milestone 2: packaged inference + API",
     "Integrate artifact, inference pipeline and API in the project with tests and usage documentation.",
     "Tagged project release candidate; submit for review.",
     "w5d1-w5d5.", "-")
unit("w5d7_review", "Review and catch-up (light)", REVIEW,
     "Week 5 retrieval sheet; ML system design rep 1 (45 min, rubric after).", "Week 5 units.", "-")

# ---------------------------------------------------------------- Week 6
unit("w6d1_docker_basics", "Docker I: images, layers and a correct Dockerfile",
     "Explain what an image and container are; write a Dockerfile for the API (non-root, .dockerignore, cache-friendly layer order) and run it locally.",
     "Local container serving predictions; image build is repeatable.",
     "w5d6; Docker Engine installed on Pop!_OS.", "H12.1")
unit("w6d2_docker_reproducibility", "Docker II: pinned dependencies, multi-stage builds, smoke tests",
     "Make the environment reproducible (lockfile, pinned base image digest), reduce image size, and smoke-test the container.",
     "Multi-stage image with lockfile and an automated container smoke test.",
     "w6d1.", "H12.2")
unit("w6d3_ci", "Continuous integration with GitHub Actions",
     "Automate lint, tests and image build on every push; decide what belongs in CI versus scheduled evaluation jobs.",
     "Green CI workflow on the project repository with caching.",
     "w6d2, w1d6.", "H14.1")
unit("w6d4_latency_resources", "Latency, throughput and resource use",
     "Measure p50/p95/p99 latency and memory under load, find the bottleneck, and tune workers/batching against a stated budget.",
     "Load-test report with method, percentiles and one evidence-based optimisation.",
     "w6d1.", "H10.4, H15.1")
unit("w6d5_cloud_deployment", "One small cloud deployment on AWS (authorisation-gated)",
     "Understand IAM, credentials, registries and cost; deploy the container by one route, or complete the fully local equivalent if cloud use is not authorised.",
     "Deployment runbook; either a deployed endpoint (with explicit authorisation and teardown) or a local dry-run with the same configuration.",
     "w6d2; AWS account decisions made by you; cost briefing read.", "H13.1, H13.2")
unit("w6d6_cd_ops_debugging", "Delivery and operational debugging; project milestone 3",
     "Promote an image by tag, configure through environment, read logs to diagnose seeded failures, and roll back.",
     "Debugging log for three seeded failures + rollback demonstration.",
     "w6d3, w6d5.", "H14.2, H15.2")
unit("w6d7_review", "Review and catch-up (light)", REVIEW,
     "Week 6 retrieval sheet; interview set 6 (debugging narrative + Python, timed).", "Week 6 units.", "-")

# ---------------------------------------------------------------- Week 7
unit("w7d1_service_logging_metrics", "Structured logging and service metrics",
     "Emit structured request and prediction logs with correlation ids; define the service's golden signals (traffic, errors, latency, saturation).",
     "Structured logs + metrics endpoint; a query that answers 'what happened to request X'.",
     "w5d6, w1d4.", "H15.1")
unit("w7d2_input_monitoring_drift", "Input monitoring and drift statistics",
     "Detect schema violations, range and missingness changes and distribution shift (PSI, KS, Wasserstein) with windows and thresholds chosen for an acceptable false-alarm rate.",
     "Drift monitor with a measured false-alarm rate on stable data.",
     "w7d1, w3d5.", "H15.3")
unit("w7d3_drift_vs_degradation", "Drift is not degradation: delayed labels and measured performance",
     "Separate input change from measured performance loss; design label backfill, proxy metrics and delayed evaluation.",
     "Replay experiment showing drift without degradation and degradation without flagged drift.",
     "w7d2.", "H15.4")
unit("w7d4_model_updates_rollback", "Model updates: retraining triggers, shadow and canary, rollback",
     "Define when and how a model is replaced: triggers, offline gate, shadow/canary comparison, versioned rollback.",
     "Update and rollback procedure exercised locally with two model versions.",
     "w5d2, w7d3.", "H15.5")
unit("w7d5_reliability", "Reliability and failure handling",
     "Handle bad input, timeouts, missing models and dependency failures deliberately: guards, fallbacks, degradation, failure-injection drills.",
     "Failure-injection test suite and a short incident note.",
     "w5d5, w7d1.", "H15.6")
unit("w7d6_project_milestone_4", "Project milestone 4: monitoring demonstration and runbook",
     "Demonstrate monitoring on a replay of held-out experiments and document operating procedures.",
     "Monitoring demo + runbook; submit for review.",
     "w7d1-w7d5.", "-")
unit("w7d7_review", "Review and catch-up (light)", REVIEW,
     "Week 7 retrieval sheet; ML system design rep 2 (45 min, spoken).", "Week 7 units.", "-")

# ---------------------------------------------------------------- Week 8
unit("w8d1_project_completion", "Project completion audit: reproduce from a clean clone",
     "Audit the project against the deliverables checklist and reproduce every headline number from a fresh clone.",
     "Clean-clone reproduction log; gap list closed or explicitly scoped out.",
     "Milestones 1-4.", "H8.3")
unit("w8d2_report_limitations", "Technical report and model limitations",
     "Write a short technical report and a limitations section that a sceptical reviewer would accept.",
     "4-page report, model card, limitations.",
     "w8d1.", "H16.2")
unit("w8d3_system_design", "ML system design",
     "Apply a repeatable structure (requirements, data, labels, evaluation, serving, monitoring, iteration) to two timed designs, one in an unfamiliar domain.",
     "Two written designs scored against the rubric.",
     "Weeks 5-7.", "H16.3")
unit("w8d4_coding_interviews", "Coding and SQL interviews, timed",
     "Solve Python data-structure and SQL problems under time pressure while explaining aloud.",
     "Timed set results and an error log by pattern.",
     "Recurring interview reps.", "H16.4")
unit("w8d5_project_explanation", "Explaining the project and defending tradeoffs",
     "Deliver 5-minute and 20-minute walkthroughs and answer adversarial questions on evaluation, limitations and alternatives.",
     "Recorded walkthrough + written answers to ten hard questions.",
     "w8d2.", "H16.2")
unit("w8d6_final_assessment", "Final independent assessment",
     "Complete a parallel form of the diagnostic and the final transfer task unassisted, for comparison with Week 1 evidence.",
     "Final assessment submission.",
     "All previous weeks.", "-")
unit("w8d7_retrospective", "Retrospective and evidence portfolio (light)",
     "Compare Week 1 and Week 8 evidence, list what is demonstrated versus still unassessed, plan the next eight weeks.",
     "Evidence portfolio index and personal next-steps plan.", "w8d6.", "-")


def main() -> None:
    (ROOT / "course.json").write_text(json.dumps({"units": U}, indent=2) + "\n")
    lines = ["# Schedule: every session at a glance", "",
             "Generated by `python tools/build_course.py` - edit that file, not this one.",
             "Status meanings are in [docs/AUTHORING.md](../docs/AUTHORING.md). "
             "**Planned** units have objectives only; their material is not written yet.", ""]
    for week, theme in WEEK_THEMES.items():
        lines += [f"## Week {week} - {theme}", "",
                  "| Day | Unit | Primary objective | Deliverable | Prerequisites | Handbook | Status |",
                  "|---|---|---|---|---|---|---|"]
        for u in (x for x in U if x["week"] == week):
            name = f"[{u['title']}](../{u['path']}/README.md)" if u["path"] else u["title"]
            lines.append(f"| {u['day']} | `{u['id']}`<br>{name} | {u['objective']} | {u['deliverable']} | "
                         f"{u['prerequisites']} | {u['handbook']} | {u['status']} |")
        lines.append("")
    (ROOT / "roadmap" / "SCHEDULE.md").write_text("\n".join(lines))
    print(f"wrote course.json ({len(U)} units) and roadmap/SCHEDULE.md")


if __name__ == "__main__":
    main()
