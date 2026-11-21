# Status

Last updated: 2026-11-21, end of the first authoring session.
Labels are defined in [docs/AUTHORING.md](docs/AUTHORING.md). Nothing here records a learner
result: **no diagnostic submission has been received**, so no personalisation has been applied.

## Summary

| | Count |
|---|---|
| Sessions scheduled | 56 (48 core, 8 light) |
| Sessions with complete material | 5 (diagnostic sessions w1d1-w1d2; lessons w1d3, w1d4, w1d5) |
| Sessions planned (objective, deliverable, prerequisites only) | 51 |
| Handbook sections written | 3 of about 45 (H2.1, H2.2, H9.1) |

The course is **not** complete. Roughly one week of eight has full material.

## Authored and execution verified

Verified on Python 3.13.18 with the versions in [docs/TESTED_VERSIONS.md](docs/TESTED_VERSIONS.md).
"Checks verified" means `python tools/verify_checks.py --all` was run on the final tree: each
reference solution passes its checks and each plausible wrong submission is rejected (full run: 5 min 6 s).

| Unit | Material | Checks verified | Also executed |
|---|---|---|---|
| Diagnostic `a1_python` | task, starter, solution, notes | solution passes; 3 wrong submissions rejected | starter fails as intended |
| Diagnostic `a2_sql` | task, SQLite db, solution, notes | passes; 4 rejected | starter fails |
| Diagnostic `a3_cleaning` | task, dirty table, solution, notes | passes; 4 rejected | starter fails |
| Diagnostic `b1_baseline` | task, data, solution, notes | passes; 3 rejected | starter fails |
| Diagnostic `b2_leakage` | task, data, solution, notes | passes; 4 rejected | starter fails |
| Diagnostic `b3_testing_api` | task, solution, notes | passes; 4 rejected | learner tests graded by running them against broken implementations |
| Diagnostic `b4_explain` | written task, rubric | none (rubric only) | - |
| Lesson `w1d3_package_structure` | all 8 sections, example, lab, challenge, 3 hints, assessment | lab: passes, 5 rejected; challenge: passes, 4 rejected | fresh venv + `pip install -e` + `pumpwatch train` from another directory reproduced the reference metrics; worked example installed and run |
| Lesson `w1d4_config_logging` | all 8 sections, example, lab, challenge, 3 hints, assessment | lab: passes, 6 rejected; challenge: passes, 3 rejected | two runs with the same config gave identical metrics; changing the split seed changed the held-out units |
| Lesson `w1d5_testing_ml_code` | all 8 sections, example, lab, challenge, 3 hints, assessment | lab: passes, 5 weak test suites rejected; challenge: passes, 3 rejected | reference suite kills all 14 injected defects; shipped starter kills none |
| Diagnostic data generator | `diagnostic/data/make_data.py` | - | two runs byte-identical |
| Pump data generator | `data/make_pump_data.py` | - | regeneration byte-identical to the committed file |
| Project data access | `project/get_skab.py` | - | 35 files downloaded and re-verified against the manifest; dataset facts in `project/README.md` computed from them |
| Tooling | `wb.py`, `tools/` | - | `status`, `next`, `check` exercised |

Continuous integration: `.github/workflows/ci.yml` repeats the checks verification on Python 3.11,
3.12 and 3.13. First-run result: see "CI result" at the end of this file.

## Reviewed (prose)

| Section | Review state |
|---|---|
| H2.1 Project structure, environments, packaging | Checked against the source files of the Python Packaging User Guide, setuptools docs, CPython `venv`/`sys.path` docs and uv docs (read from their GitHub repositories), plus `uv --help` 0.11.32 |
| H2.2 Configuration, logging, reproducible runs | Checked against CPython logging/tomllib/dataclasses doc sources, NumPy random compatibility policy, scikit-learn glossary, PyTorch randomness notes, 12-factor config (GitHub sources) |
| H9.1 Unit-testing ML code | Checked against pytest doc sources (fixtures, parametrize, tmp_path, good practices) and installed docstrings of `pytest.approx`, `pytest.raises`, `numpy.testing.assert_allclose` |

Each section lists the pages opened and flags what was written from memory.

## Planned (not written)

Every unit marked Planned in [roadmap/SCHEDULE.md](roadmap/SCHEDULE.md): w1d6, w1d7 and all of
Weeks 2-8. Handbook chapters 1, 3-8, 10-16 and sections H2.3, H9.2. The interview prompt bank
beyond the three reps inside the authored lessons. The transfer exercise on a public business dataset.

## Known limitations

1. **Single authoring pass.** Lesson and handbook prose was written and checked by its author against
   sources, but has not had an independent second read. Treat explanations as carefully drafted, and
   report anything that looks wrong.
2. **One Python version executed locally** (3.13). 3.11 and 3.12 are covered only by CI.
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
9. **The w1d5 lab tests package v0.1.0** (the w1d3 result), not the v0.2.0 package from w1d4. The
   lesson says your own package can be substituted.
10. **Not yet verified for later weeks:** the AWS route and its costs, FastAPI and Docker specifics,
    and the licence of the candidate transfer dataset (UCI Bank Marketing). Nothing depends on them yet.
11. **SKAB is GPL-3.0** and is downloaded, not redistributed. Sample-level anomaly prevalence is about
    35 % and there are only 34 events; the project brief treats both as constraints on what can be claimed.

## Next exact continuation step

1. **Learner:** sit the diagnostic (w1d1, w1d2) and push `diagnostic/*/lab/` plus `diagnostic/SUBMISSION.md`.
2. **Author, on receiving it:** review against `solutions/diagnostic/SCORING.md`; record outcomes in
   `progress/SKILLS_LEDGER.md` (evidence log and "Demonstrated" section); apply the adaptation rules to
   w1d3-w1d6 and Weeks 2-3 by editing `tools/build_course.py`.
3. **Author, independent of the submission:** write `w1d6_notebook_to_package` (exploratory notebook on
   SKAB, `flowguard` skeleton, Git workflow) with handbook H2.3, then `w1d7_review` (Week 1 retrieval
   sheet and interview set 1), then Week 2 starting at `w2d1_sql_joins_grain` with H3.1. Follow
   `docs/AUTHORING.md`; run `python tools/verify_checks.py --all` before changing any status.

## CI result

Pending at the time of writing; updated below once the first run finishes.
