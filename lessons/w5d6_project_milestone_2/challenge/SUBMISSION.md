# Milestone 2 submission: flowguard release candidate

<!-- Fill every field. Replace every TODO. Graded by structure checks and by a reviewer with the
     rubric in lessons/w5d6_project_milestone_2/assessment.md. -->

Repository: TODO (URL of your flowguard repository)
Commit: TODO (hash of the commit the release candidate was built from)
Tag: TODO (the release tag, e.g. v0.6.0-rc1)
Build command: TODO (the exact command that builds the model bundle, e.g. `make model RAW=...`)
Release notes: TODO (path of the release notes or CHANGELOG section inside the repository)
Time spent: TODO (hours)

## Checklist

Tick each item (`- [x]`) or mark it `- [n/a]` with a one-line reason. No unticked boxes.

- [ ] Evaluation, `predict-batch` and the API all call the same scoring function; nothing re-implements the formula.
- [ ] A parity test compares the three paths on the same data with a stated tolerance.
- [ ] The bundle is built by one command from the config and the frozen split manifest.
- [ ] The bundle records provenance: config hash, manifest hash, data identification, package version.
- [ ] Loading refuses a bundle whose files do not match their checksums.
- [ ] One version number, defined in one place; bundle and `/version` report it.
- [ ] CHANGELOG has an entry for this version, including fixes and behaviour changes.
- [ ] Tests exist at every layer: unit, integration (bundle on disk), API (TestClient), parity.
- [ ] `make test` passes from a clean clone without downloaded data.
- [ ] The README Usage block runs as written (build, test, batch predict) and shows a curl call.
- [ ] The service was started once on 127.0.0.1 and answered `/readyz` and `/predict`; it was stopped afterwards.
- [ ] No model files, predictions, raw data or credentials are committed (`.gitignore` checked).

## Self-review

Score each row 1 (below expectations), 2 (meets) or 3 (exceeds), using the rubric in
`assessment.md`. Evidence: at least one concrete sentence pointing at a file, a number or a command.

| Criterion | Score | Evidence |
|---|---|---|
| Single source of inference | TODO | TODO |
| Artifact and provenance | TODO | TODO |
| Tests at every layer | TODO | TODO |
| API contract | TODO | TODO |
| Versioning and changelog | TODO | TODO |
| Documentation and usability | TODO | TODO |
| Repository hygiene | TODO | TODO |

## Questions for the reviewer

- TODO (at least one specific question you want feedback on)
