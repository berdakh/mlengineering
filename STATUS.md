# Status

Last updated: 2026-11-22, after Week 5's core days were completed.
Labels are defined in [docs/AUTHORING.md](docs/AUTHORING.md). Nothing here records a learner
result: **no diagnostic submission has been received**, so no personalisation has been applied.

## Summary

| | Count |
|---|---|
| Sessions scheduled | 56 (48 core, 8 light) |
| Sessions with complete, verified material | 34: Weeks 1-4 complete; Week 5 core days complete |
| Sessions planned or in progress | 22: w5d7 and Weeks 6-8 (Week 6 is being written) |

The course is **not** complete. The per-session state is always in [roadmap/SCHEDULE.md](roadmap/SCHEDULE.md);
the handbook index is [handbook/README.md](handbook/README.md).

## Authored and execution verified

Verified on Python 3.13.18 with the versions in [docs/TESTED_VERSIONS.md](docs/TESTED_VERSIONS.md).
`python tools/verify_checks.py --all` was run on the full Week 1-2 tree on 2026-11-21: every reference
solution passes its checks and all 115 plausible wrong submissions are rejected.

| Unit | Checks verified | Also executed |
|---|---|---|
| Diagnostic (6 checked sections + written b4) | 22 wrong submissions rejected | starters fail as intended; data generator byte-reproducible |
| w1d3 package structure | lab 5, challenge 4 rejected | real `pip install -e` in a fresh venv; metrics reproduced from another directory |
| w1d4 config, logging, runs | lab 6, challenge 3 | identical metrics across two identical runs |
| w1d5 testing ML code | lab 5, challenge 3 weak suites rejected | reference suite kills all 14 injected defects |
| w1d6 notebook to package | lab 7, challenge 4 | reference `flowguard summary` on real SKAB: 35 experiments, 46,806 rows |
| w1d7, w2d7 review days; interview sets 1-2 | reference answers pass their tests; 10 wrong answers rejected | - |
| w2d1 SQL I | lab 5, challenge 4 | graded on the shipped and on a re-seeded database; identical results on DuckDB 2.0.1 |
| w2d2 SQL II | lab 7, challenge 3 | SQL and pandas agree with an independent oracle on two databases |
| w2d3 ingestion and quality | lab 4, challenge 4 | reference ingest on real SKAB: 46,806 rows, 0 errors, 1 warning; two runs byte-identical |
| w2d4 framing and splits | lab 6, challenge 5 | real split: 9 test, 25 development experiments; row-level vs experiment-level ROC-AUC 0.986 vs 0.849 |
| w2d5 feature pipeline | lab 5, challenge 4 | real data: 46,806 rows x 156 columns; 9.1 s cold, 0.46 s cached |
| w2d6 baselines and metrics | lab 5, challenge 4 | real baseline table (test PR-AUC 0.373 constant, 0.805 burn-in z-score, 0.827 logistic regression) |

Continuous integration repeats the checks verification on Python 3.11, 3.12 and 3.13 (see "CI result").

## Reviewed (prose)

Each handbook section ends with "sources and verification status": the pages its author opened and
what was written from memory. Rendered documentation sites were blocked, so official documentation
was read from source repositories on GitHub (CPython, packaging, setuptools, uv, pytest, pandas,
scikit-learn, PostgreSQL, Git, ruff). Paper and book citations are mostly from memory and labelled so.

## Planned (not written)

Weeks 3-8 (42 sessions) and their handbook sections; interview sets 3 onward. Week 3 is in progress.

## Known limitations

1. **Single authoring pass.** Lesson and handbook prose was written and checked by its author against
   sources, but has not had an independent second read. Treat explanations as carefully drafted, and
   report anything that looks wrong.
2. **One Python version executed locally** (3.13). 3.11 and 3.12 are covered by CI for the checks
   verification only; worked examples and the real `pip install -e` test ran on 3.13 alone.
3. **Not run on Pop!_OS.** Statements about Pop!_OS 22.04 (system Python 3.10, `python3-venv`,
   the deadsnakes PPA) and `uv python install` are from memory, flagged as unverified in H2.1.
4. **Rendered documentation sites were unreachable** from the authoring environment
   (docs.python.org, packaging.python.org, docs.pytest.org, numpy.org and others). The same documents
   were read from their source repositories on GitHub. External links in the text were not click-tested.
5. **Citations from memory**, labelled where they occur: Higham and Jia & Harman in H9.1; YAML 1.1
   typing pitfalls, pydantic and Hydra defaults, reproducibility terminology in H2.2.
6. **Time boxes are estimates.** No one has yet sat the diagnostic or the lessons against the clock.
7. **Synthetic data in Week 1 and the diagnostic.** It supports conclusions about code and reasoning,
   none about model quality. Two honest consequences are stated in the material: in w1d3 removing the
   scaling leak leaves the printed metrics unchanged; in diagnostic b2 only the two leaky columns
   inflate the score (average precision 0.955 leaky versus 0.209 honest), while the random split and
   all-rows preprocessing have no measurable effect on that data.
8. **Diagnostic visibility.** Solutions, scoring guidance and the broken implementations used to grade
   your tests (`diagnostic/b3_testing_api/checks/impls/`) are in the repository. The diagnostic is
   only informative if you do not open them first.
9. **Project snapshots differ slightly between lessons.** Each project lesson ships its own snapshot of
   upstream `flowguard` modules written to `docs/FLOWGUARD_SPEC.md`; small differences exist (for example
   whether `load_raw` sorts). Your own project repository is the single real implementation.
   Also: the w2d4 split manifest (v1) does not keep experiments with duplicated rows together; w3d1 fixes this.
   The transfer exercise uses SYNTHETIC business data because UCI Bank Marketing could not be reached
   to verify access and licence.
   **The w1d5 lab tests package v0.1.0** (the w1d3 result), not the v0.2.0 package from w1d4. The
   lesson says your own package can be substituted.
10. **Not yet verified for later weeks:** the AWS route and its costs, FastAPI and Docker specifics,
    and the licence of the candidate transfer dataset (UCI Bank Marketing). Nothing depends on them yet.
11. **SKAB is GPL-3.0** and is downloaded, not redistributed. Sample-level anomaly prevalence is about
    35 % and there are only 34 events; the project brief treats both as constraints on what can be claimed.

## Next exact continuation step

1. **Learner:** sit the diagnostic (w1d1, w1d2) and push `diagnostic/*/lab/` plus `diagnostic/SUBMISSION.md`.
2. **Author:** finish w5d7 and Week 6 (in progress), then Week 7 (`w7d1_service_logging_metrics` ...) and Week 8,
   following `docs/AUTHORING.md`, `docs/FORK_BRIEF.md` and `docs/FLOWGUARD_SPEC.md`; after each week run
   `python tools/verify_checks.py --all`, update `tools/build_course.py`, the handbook index and this file.
3. **Author, on receiving the diagnostic:** review against `solutions/diagnostic/SCORING.md`, record outcomes
   in `progress/SKILLS_LEDGER.md`, and apply the adaptation rules.

## Notes on authoring history

* All real-data results from Week 3 on use the frozen split manifest
  `solutions/lessons/w3d1_leakage/lab/splits/v2.json` (7 test, 27 development experiments). Week 2 used v1
  (9 test, 25 development); w3d1 explains the repair. A consistency pass re-ran w3d3-w3d6 on v2.
* Per-lesson verification records (commands, outcomes, sources opened, what is from memory) are at the end of
  each lesson README and in each handbook section's "sources and verification status".
* CI (`.github/workflows/ci.yml`) re-runs the full checks verification on Python 3.11, 3.12 and 3.13 on every
  push and installs CPU-only PyTorch for w4d3.

## CI result

Run 44946762192 on commit `c87b6ff` (2026-11-21): **passed on Python 3.11, 3.12 and 3.13**. Each job
ran `python tools/verify_checks.py --all` (5-8 minutes) with the newest packages satisfying
`requirements.txt`. Exact package versions resolved in CI were not recorded.
