# Assessment answers - w6d2 Docker II

## Reasoning questions

**1. Two correct builds, two numpys.** `RUN pip install -r requirements.txt` is cached on its text and
on the layers above it, not on what the index contains. The laptop reuses the layer it built weeks
ago, when the newest numpy matching the range was, say, 2.5.3. The CI runner starts with a cold cache,
runs the instruction now, and resolves the same ranges to today's newest release (2.5.5 in this
lesson's resolution). Both satisfy every specifier, so both are "correct" builds of the commit; they
are simply different environments. The cure is to make the build *read* a lock instead of resolving.
*Common wrong answer:* "Docker is nondeterministic". Docker did exactly what the recipe says.

**2. Several hashes, one file.** A released version consists of several distribution files: wheels
for each platform and Python version (manylinux x86_64, aarch64, macOS, Windows, ...) and usually an
sdist. The lock lists the sha256 of every file that is acceptable for that version, so the same lock
works wherever a matching wheel exists. pip picks the file it would install, downloads it, computes
its sha256 and refuses to install if it is not in the list. This prevents a tampered mirror or a
compromised index from serving different bytes under the same name and version, and it prevents
accidental substitution (a re-uploaded file, a private index shadowing PyPI). It also forces the lock
to be complete: in hash-checking mode every requirement must be pinned with `==`.
*Common wrong answer:* "hashes pin the version". `==` pins the version; the hash pins the *file*.

**3. Platform manifest digest.** `python:3.12-slim` is a multi-platform *index* whose entries are
per-architecture manifests. Pinning the amd64 manifest digest makes `FROM` resolve to the amd64 image
everywhere. On an arm64 machine (Apple Silicon laptop, ARM CI runner, Graviton cloud host) the build
either fails or runs the amd64 image under emulation, slowly. Pin the index digest; each platform then
pulls its own variant of the same release.

**4. Why multi-stage is larger here.** (a) The lock resolved pandas 3.1.1 (82.4 MB installed) where
w6d1's top-level pins got 3.0.5 (74.1 MB): +8 MB. (b) The runtime venv has no pip, saving 6.9 MB, but
nothing else: every dependency installs from wheels, so the builder needed no compiler or headers
that could be left behind. Net +7 MB. Changes that would really reduce size: serve without pandas (it
is 48 % of the installed packages and the service uses it for a few lines; numpy alone suffices), or a
smaller base (distroless or a custom minimal image), not more stages.

**5. What a passing smoke test does not establish.** (a) Model quality: the fixture is 300 synthetic
samples; detection performance is the evaluation of Weeks 3-4 on held-out experiments. (b) Performance:
latency and memory under concurrent load (w6d4). (c) Behaviour on inputs unlike the fixture: invalid,
extreme or long requests (the API tests of w5d4-w5d5) and distribution shift in production (Week 7
monitoring). (d) Operational behaviour such as graceful shutdown (w6d1's live check) and correct
configuration in the target environment (w6d5, w6d6).

**6. `ARG REVISION` in the runtime stage, late.** The Dockerfile reference: an `ARG` declared inside a
stage is visible in that stage and in stages based on it, not in unrelated stages; an `ARG` declared
before the first `FROM` is visible only to `FROM` lines unless redeclared (without a value) inside a
stage. The runtime stage is not based on the builder, so it must declare `ARG REVISION` itself to use
it in a label. Late, because every `RUN` after an `ARG` sees it as an environment variable, so a new
commit hash would bust the cache of every later `RUN`; declaring it in the runtime stage, after the
expensive work (done in the builder), keeps the dependency install cached. In the reference the only
`RUN` after it is `useradd` (0.1 s).

## Explain a design choice: pin, and update deliberately (model answer)

The colleague is right that a pinned environment does not receive fixes by itself: a lock pins known
vulnerabilities as faithfully as it pins good versions. Running "the newest" every build, however,
means that the code that is evaluated, tested and approved is not the code that is deployed: any
nightly rebuild can change numerical behaviour (the challenge is a small version of a real class of
incidents) and an incident cannot be reproduced because the environment no longer exists.

Pinning buys three things: what was tested is what runs; any image can be rebuilt equivalently later
(debugging, audits, rollbacks); and every change of a dependency becomes a reviewable diff.

Both goals are met by making updates frequent and routine instead of implicit: a scheduled job (or a
bot) recompiles the lock and bumps the base digest weekly, opens a pull request, CI builds the image,
runs unit tests, the smoke test and an evaluation on held-out data, and a person merges it. Security
advisories are checked against the lock (it is the inventory) and trigger the same pipeline out of
schedule. Rollback is deploying the previous image tag, which still exists unchanged.

*Rubric notes.* Strong answers concede the staleness risk, name reproducibility and reviewability, and
describe an automated, tested update path with a time bound.

## Challenge: what the reference report contains, and common mistakes

The reference `DRIFT_REPORT.md` is in `solutions/.../challenge/`. Points a strong report makes: the
build resolves a range at build time; 1.1.0 appeared in the index; it changed `calibrate` from the
population SD (divide by n) to the sample SD (n - 1), shrinking every z-score by 1/sqrt(20/19) (about
2.5 %) with the 20-sample burn-in; the fix pins 1.0.0 with its hash and installs with
`--require-hashes`; and an upgrade to 1.1.0 must be a deliberate change that re-validates the operating
point (the threshold was chosen with the population SD).

| Mistake | Why it fails |
|---|---|
| Compile the lock today and commit it | pins 1.1.0, the newest, not the validated version: reproducible, but reproducibly wrong |
| `zscorelib==1.0.0` without a hash | pip in hash-checking mode refuses: "Hashes are required in --require-hashes mode, but they are missing from some requirements" |
| Hash copied from the other wheel | "THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE ... Expected sha256 c09a... Got 693c..." |
| `zscorelib>=1.0,<1.1` with a hash | "In --require-hashes mode, all requirements must have their versions pinned with ==" |
| A correct lock that build.sh does not use | the build still resolves requirements.in and still installs 1.1.0 |
| "Update the expected scores to the new output" | makes the test pass by redefining correct; the operating point was validated with 1.0.0 |

## Interview rep: reproducible model images - what a strong answer contains

* **Artifacts:** `requirements.in` and a hash-locked `requirements.lock` in Git; the base image pinned
  by index digest; the model bundle with its own version and checksum (w5d2); the image pushed to a
  registry under an immutable tag (commit SHA plus model version) with OCI labels; the evaluation report
  and smoke fixture tied to that tag.
* **Build:** only from the lock (`--require-hashes`), multi-stage, non-root, no secrets; build arguments
  for revision and version.
* **CI:** unit tests, image build, container smoke test against recorded outputs, evaluation on the
  frozen test set for model changes, vulnerability scan against the lock; a regular cache-free build to
  surface hidden drift.
* **Updates:** weekly automated PR that recompiles the lock and bumps the base digest, with the same
  checks; emergency path for critical advisories; review of the lock diff.
* **Rollback:** redeploy the previous immutable tag; never rebuild an old commit to roll back.
* **Retraining:** a new model is a new bundle version; the image either bakes it (new tag) or loads it
  by version, and every prediction reports the model version.

| Criterion | Strong | Weak |
|---|---|---|
| Pins all three moving inputs (base, closure, files) | yes | "pin requirements" |
| Separates code, environment and model versions | yes | one version for everything |
| Tested, scheduled updates | yes | "update when needed" |
| Rollback by immutable artifact | yes | "rebuild the old version" |
