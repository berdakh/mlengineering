# Deliverables audit: reference flowguard (course solutions)

Audited 2026-11-22 against the checklist in `project/README.md`. Evidence paths are relative to the course
repository, because the reference project is assembled from the milestone solutions; in your own
repository they point at your files. Status: `done`, `partial` or `scoped out`.

| Deliverable | Status | Evidence or reason |
|---|---|---|
| Problem statement and stakeholder needs | done | `solutions/labs/w2d4_problem_framing_splits/lab/PROBLEM_STATEMENT.md` |
| Dataset provenance and data dictionary | done | `project/README.md` (licence, pinned commit, data dictionary) and `project/get_skab.py` (SHA-256 manifest) |
| Versioned split definitions | done | `solutions/labs/w3d1_leakage/lab/splits/v2.json` (frozen; supersedes v1 for the reason in w3d1) |
| Reproducible preprocessing | done | `solutions/labs/w4d6_project_milestone_1/lab/Makefile` (`make evaluate` rebuilds the tidy table) |
| Simple baseline | done | `solutions/labs/w2d6_baselines_metrics/lab/` and the constant / clock rows in the w2d6 lesson |
| Evidence-based model comparison | done | `solutions/labs/w4d6_project_milestone_1/example_report/evaluation.md` (intervals, MPID, Pareto) |
| Error analysis | done | `solutions/labs/w3d6_error_analysis_transfer/` and the per-experiment table in the w4d6 report |
| Training and evaluation commands | done | `make evaluate`; reproduced from a clean clone in `solutions/labs/w8d1_project_completion/real_audit/REPRODUCTION_LOG.md` |
| Packaged inference | done | `solutions/labs/w5d6_project_milestone_2/example_release/parity.json` (evaluation = batch = API, max difference 0.0) |
| Tests | done | `solutions/labs/w5d6_project_milestone_2/lab/tests/` and the check suites of every milestone |
| Prediction API | done | `solutions/labs/w5d6_project_milestone_2/example_release/API_TRANSCRIPT.md` |
| Container | done | `solutions/labs/w6d2_docker_reproducibility/lab/Dockerfile` (multi-stage, lockfile, smoke test) |
| One deployment (authorisation-gated) | partial | The AWS route was prepared and dry-run only; no live deployment was authorised, so the local container run with the same configuration stands in for it (see w6d5) |
| Monitoring demonstration | done | `solutions/labs/w7d6_project_milestone_4/example_demo/monitoring_demo.md` |
| README, model limitations, short technical report | done | `solutions/labs/w8d2_report_limitations/reference/TECHNICAL_REPORT.md` and `MODEL_CARD.md` |
