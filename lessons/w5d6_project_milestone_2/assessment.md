# Assessment — w5d6 project milestone 2

## Milestone rubric (the reviewer scores your submission with this)

| Criterion | 1 - below expectations | 2 - meets | 3 - exceeds |
|---|---|---|---|
| Single source of inference | formula duplicated somewhere | one formula; parity tested on synthetic data | also parity on the real data, with the result in the release notes |
| Artifact and provenance | bundle without provenance | config and manifest hashes recorded | also data identification and code version; load refuses mismatches |
| Tests at every layer | unit only | unit, integration, API, parity | also error paths, concurrency and a contract baseline |
| API contract | happy path only | 422/413/503 semantics documented and tested | versioned schema with a compatibility policy |
| Versioning and changelog | numbers disagree | one version, CHANGELOG entry | entry explains behaviour changes for users |
| Documentation and usability | README missing steps | Usage block runs as written | a newcomer could also debug a failed build from it |
| Repository hygiene | artifacts or data committed | `.gitignore` covers models, predictions, data | clean tag, small focused commits |

## Reasoning questions

1. Why is a two-way parity test (evaluation vs batch) not enough here? Construct a defect it misses.
2. The parity test compares floats read from a CSV. What tolerance did you choose and why? What did
   you observe with pandas' default parser on the real data?
3. The bundle records the sha256 of `splits/v2.json`. What question does that answer, and for whom?
4. The `anomaly-free` recording has 9,405 rows and `/predict` accepts at most 3,600 values. Why do
   chunked API scores equal batch scores exactly for this model, and for which kind of model would
   chunking with a shared burn-in *not* reproduce batch scores?
5. Three version numbers appear in `/version` and the bundle (package, API schema, model). Give an
   example change that bumps each one and only that one.

## Design choice (6-10 sentences)

`build-model` packages a configuration chosen in w4d5 instead of re-choosing the threshold on every
build. Argue for this, then argue for re-choosing the threshold at build time from the development
experiments, and say what each choice requires from the provenance record.

## Interview rep (project explanation, 10 minutes, spoken)

"Walk me through what happens when a client calls `/predict`, from the HTTP request to the number it
gets back, and tell me how you know that number is the one your evaluation report used." Record
yourself or say it aloud without notes; then score it with the checklist in the answers file.
