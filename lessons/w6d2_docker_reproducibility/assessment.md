# Assessment - w6d2 Docker II

Answer before opening `solutions/lessons/w6d2_docker_reproducibility/assessment_answers.md`. 20-25 minutes.

## Reasoning questions

1. Your image builds fine on your laptop every day, but the CI build of the same commit installs a
   different numpy. Both use the same Dockerfile with `RUN pip install -r requirements.txt` (ranges).
   Explain how both can be "correct builds" of the same commit.
2. Why does the lock list several hashes for `numpy==2.5.5` but you install only one file? What
   exactly does pip check, and what attack or accident does that prevent?
3. A colleague pins the base image to the *amd64 manifest* digest from `imagetools inspect` instead of
   the index digest. What breaks, and for whom?
4. The multi-stage image in this lab is 7 MB larger than the single-stage one. Give the two causes
   (from the measurements) and one change that would really reduce the size.
5. Your smoke test passes. List three kinds of defect it cannot detect, and for each, which check in
   this course would.
6. Why must `ARG REVISION` be declared in the runtime stage, and why late in it?

## Explain a design choice (150-250 words)

The lock pins exact versions with hashes, and upgrades happen only by recompiling it in a pull
request. A colleague argues: "We should always run the newest versions to get security fixes; pinning
makes us vulnerable." Answer them: when are they right, what does pinning buy, and what process gets
both stability and timely patches?

## Rubric for the open-ended answers

| Criterion | Strong | Adequate | Weak |
|---|---|---|---|
| Resolution vs cache (Q1) | laptop reuses a cached RUN layer resolved earlier; CI resolves the ranges afresh; both satisfy the ranges | "different caches" without the resolution point | blames Docker |
| Hash checking (Q2) | one hash per distribution file (wheels per platform + sdist); pip compares the downloaded file's sha256; prevents tampered or re-uploaded files and silent substitution | "integrity" without mechanism | thinks hashes pin versions |
| Digests (Q3) | index vs platform manifest; arm64 runners/Macs fail or emulate | "multi-arch" mentioned | no answer |
| Size (Q4) | pandas 3.1.1 vs 3.0.5 (+8 MB) outweighs pip removal (-7 MB); real lever: drop pandas from serving or smaller base | one cause | "multi-stage always smaller" |
| Smoke test limits (Q5) | quality (evaluation), load/latency (w6d4), unusual inputs (validation tests/monitoring), drift over time (Week 7) | two items | "nothing" |
| ARG scope (Q6) | stage-scoped (only inherited by stages based on it; pre-FROM ARGs only for FROM); in-scope ARGs bust later RUN caches | one of the two | no answer |
| Design choice | separates stability from staleness; scheduled/automated lock updates with tests; emergency patch path; scanning against the lock | one side argued | slogan |

## Interview rep (15 minutes, system design, reduced assistance)

> "We retrain a model weekly and deploy it as a container. Last quarter, two incidents came from
> dependency changes nobody made on purpose. Design the build and release process for the model image
> so that every deployed image can be rebuilt bit-for-bit-equivalent in behaviour a year later, and so
> that security patches still reach production within a week. Name the artifacts you store, what CI
> checks, and what a rollback looks like."

Answer aloud or in writing, timed, then self-score with the rubric in the answers file.
