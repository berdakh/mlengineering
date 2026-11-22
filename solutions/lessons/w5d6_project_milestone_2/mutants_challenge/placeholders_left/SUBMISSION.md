# Milestone 2 submission: flowguard release candidate

<!-- Reference example, filled in for the reference project in solutions/lessons/w5d6_project_milestone_2/lab.
     The commit is the course-repository commit the reference was built from; the tag is illustrative
     (no tag was created in the course repository). -->

Repository: https://github.com/berdakh/mlengineering-
Commit: 3734c415dc7e
Tag: v0.6.0-rc1
Build command: `make model RAW=data/raw/skab`
Release notes: solutions/lessons/w5d6_project_milestone_2/example_release/RELEASE_NOTES.md
Time spent: TODO (hours)

## Checklist

- [x] Evaluation, `predict-batch` and the API all call the same scoring function; nothing re-implements the formula.
- [x] A parity test compares the three paths on the same data with a stated tolerance.
- [x] The bundle is built by one command from the config and the frozen split manifest.
- [x] The bundle records provenance: config hash, manifest hash, data identification, package version.
- [x] Loading refuses a bundle whose files do not match their checksums.
- [x] One version number, defined in one place; bundle and `/version` report it.
- [x] CHANGELOG has an entry for this version, including fixes and behaviour changes.
- [x] Tests exist at every layer: unit, integration (bundle on disk), API (TestClient), parity.
- [x] `make test` passes from a clean clone without downloaded data.
- [x] The README Usage block runs as written (build, test, batch predict) and shows a curl call.
- [x] The service was started once on 127.0.0.1 and answered `/readyz` and `/predict`; it was stopped afterwards.
- [x] No model files, predictions, raw data or credentials are committed (`.gitignore` checked).

## Self-review

| Criterion | Score | Evidence |
|---|---|---|
| Single source of inference | 3 | `ZScoreModel.score` is the only formula; parity.json shows max difference 0.0 over 46,806 rows for evaluation vs batch and vs API. |
| Artifact and provenance | 2 | MANIFEST.json records config, config hash, manifest hash a9f4e243...5314 and a dev-data hash; no record of the Git commit yet. |
| Tests at every layer | 2 | 10 tests: unit, bundle round trip and tamper, API, parity with forced chunking; no concurrency test (w5d5 has one for the service). |
| API contract | 2 | flowguard-api/1 with 422/413/503 semantics and a non-echoing validation handler; no committed OpenAPI baseline or contract test yet. |
| Versioning and changelog | 3 | Version lives only in flowguard.__version__, pyproject reads it; CHANGELOG 0.6.0 records the ddof skew fix. |
| Documentation and usability | 2 | README Usage commands run as written in the checks; the burn-in requirement of /predict needs a fuller explanation. |
| Repository hygiene | 3 | models/ and predictions/ are ignored; raw SKAB data stays outside the repository under its GPL-3.0 licence. |

## Questions for the reviewer

- Should the bundle record the Git commit, and how do I do that without making the build depend on a clean working tree?
- Is chunking long recordings on the client side acceptable, or should the API accept a stream with server-side burn-in state (w5d3)?
