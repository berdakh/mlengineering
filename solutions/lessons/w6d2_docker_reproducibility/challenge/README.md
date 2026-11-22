# w6d2 independent challenge: the build that drifted

`service/driftsvc.py` is a tiny scoring service (the flowguard z-score rule on one sensor). It depends
on one package, `zscorelib`, a SYNTHETIC package made for this challenge. Its build script installs
dependencies from a local package index, `wheelhouse/`, so that the whole exercise runs offline:

```bash
cd lessons/w6d2_docker_reproducibility/challenge
./build.sh
```

Two weeks ago (2026-11-08) this printed `smoke test PASS`, and `expected/scores.json` was recorded
from that run. Today it prints `smoke test FAIL`. Nobody changed `service/`, `expected/` or
`build.sh`. (The sources of every package in the index are in `pkgsrc/`.)

## Your task

1. Find out what changed and why the build picked it up.
2. Make the build reproducible **and** correct:
   * write `service/requirements.lock`: the validated version of `zscorelib`, pinned with `==`, with the
     sha256 hash of its wheel;
   * change `build.sh` so that it installs the lock in hash-checking mode (`--require-hashes`) instead
     of resolving `requirements.in`.
3. Write `DRIFT_REPORT.md` (sections are given): what changed, why the build drifted, the fix and how
   you verified it, and how to prevent it (including how a *deliberate* upgrade should happen).

## Acceptance criteria (checked by `python wb.py check w6d2 --challenge`)

* The lock pins `zscorelib` to the version that produced the recorded scores, with `==`.
* One of its hashes is the sha256 of that version's wheel in `wheelhouse/`.
* `pip install --no-index --find-links wheelhouse --require-hashes -r service/requirements.lock`
  succeeds, and the installed package reproduces `expected/scores.json`.
* `build.sh` installs `service/requirements.lock` with `--require-hashes` and no longer reads
  `requirements.in`.
* Each of the four report sections has at least 40 words.

The written report is judged with the rubric in
`solutions/lessons/w6d2_docker_reproducibility/assessment_answers.md` after you submit.

Note on the wheels: they are committed build artifacts, like files on PyPI. Rebuilding them from
`pkgsrc/` gives wheels with different hashes (wheel archives contain timestamps), which is itself an
illustration of why locks pin hashes of the files you actually tested. (The wheels were built for the
course on 2026-11-22, so the timestamps inside them do not match the scenario's dates.)
